"""D4 metadata-only request tracing and bounded, process-local JSON metrics.

Percentiles use nearest rank over the latest 2048 non-null observations per
stage. Counters cover the process lifetime; samples are not historical storage.
No request text, exception messages, user identity, or client payload is accepted.
"""
from collections import Counter, deque
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
import json
import logging
import math
import os
from threading import Lock
import time
import uuid

from flask import current_app, has_app_context
from flask.logging import default_handler

STAGES = (
    'service_initialization', 'query_embedding', 'candidate_retrieval',
    'record_loading', 'reranking', 'context_construction', 'generation',
    'total', 'streaming_ttft', 'streaming_completion',
)
ERRORS = {
    'retrieval_failure', 'reranking_failure', 'generation_failure',
    'context_failure', 'application_error', 'streaming_interruption', 'no_results',
}
FALLBACKS = {
    'keyword_no_vectors', 'keyword_no_semantic_results', 'keyword_retrieval_error',
    'web_search', 'legacy_generation',
}
RERANK_STATES = {
    'not_reached', 'executed', 'skipped_disabled', 'skipped_unavailable',
    'skipped_empty', 'failed',
}
_active = ContextVar('rag_request_trace', default=None)
_registry_lock = Lock()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Reuse Flask's WSGI handler; leave root/service/health logging configuration alone.
if not logger.handlers:
    logger.addHandler(default_handler)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def latency_summary(values, observed_count=None):
    samples = sorted(values)
    size = len(samples)
    return {
        'count': size,
        'observed_count': size if observed_count is None else observed_count,
        'p50_ms': samples[math.ceil(size * .50) - 1] if size else None,
        'p95_ms': samples[math.ceil(size * .95) - 1] if size else None,
        'min_ms': samples[0] if size else None,
        'max_ms': samples[-1] if size else None,
        'mean_ms': sum(samples) / size if size else None,
    }


class RAGMetrics:
    def __init__(self, sample_limit=2048):
        self.lock = Lock()
        self.sample_limit = sample_limit
        self.started_at = utc_now()
        self.process_instance_id = str(uuid.uuid4())
        self.counts = Counter(started=0, completed=0, active=0, success=0,
                              failure=0, interrupted=0, normal=0, streaming=0)
        self.reranking = Counter({state: 0 for state in RERANK_STATES})
        self.fallbacks = Counter({category: 0 for category in FALLBACKS})
        self.errors = Counter({category: 0 for category in ERRORS})
        self.samples = {name: deque(maxlen=sample_limit) for name in STAGES}
        self.observed = Counter()

    def start(self, mode):
        with self.lock:
            self.counts.update(started=1, active=1)
            self.counts[mode] += 1

    def complete(self, trace, status):
        with self.lock:
            self.counts.update(completed=1)
            self.counts['active'] -= 1
            self.counts[status] += 1
            self.reranking[trace.reranking_state] += 1
            self.fallbacks.update(trace.fallbacks)
            self.errors.update(trace.errors)
            for name, value in trace.timings.items():
                if value is not None:
                    self.samples[name].append(value)
                    self.observed[name] += 1

    def snapshot(self):
        with self.lock:
            return {
                'schema_version': 1,
                'process': {
                    'pid': os.getpid(), 'instance_id': self.process_instance_id,
                    'started_at_utc': self.started_at, 'reset_at_utc': self.started_at,
                    'scope': 'single_worker_process_local',
                    'reset_policy': 'new_process_or_app_instance_resets_all_metrics',
                    'persistent': False,
                },
                'requests': dict(self.counts),
                'reranking': dict(self.reranking),
                'fallbacks': dict(self.fallbacks), 'errors': dict(self.errors),
                'latency': {
                    'unit': 'milliseconds', 'percentile_method': 'nearest_rank',
                    'sample_window': 'latest_non_null_observations_per_stage',
                    'sample_limit': self.sample_limit,
                    'stages': {name: latency_summary(samples, self.observed[name])
                               for name, samples in self.samples.items()},
                },
            }


_process_metrics = RAGMetrics()


def get_metrics():
    if not has_app_context():
        return _process_metrics
    with _registry_lock:
        if 'rag_metrics' not in current_app.extensions:
            current_app.extensions['rag_metrics'] = RAGMetrics()
        return current_app.extensions['rag_metrics']


class RequestTrace:
    def __init__(self, mode, request_id=None, metrics=None):
        if mode not in ('normal', 'streaming'):
            raise ValueError('unknown RAG runtime mode')
        try:
            self.request_id = str(uuid.UUID(request_id)) if request_id else str(uuid.uuid4())
        except (ValueError, TypeError, AttributeError):
            self.request_id = str(uuid.uuid4())
        self.mode = mode
        self.started = time.perf_counter()
        self.metrics = metrics if metrics is not None else get_metrics()
        self.timings = dict.fromkeys(STAGES)
        self.fallbacks = set()
        self.errors = set()
        self.error_occurrences = 0
        self.reranking_state = 'not_reached'
        self.candidate_count = None
        self.outcome = None
        self.stream_completed = False
        self.finished = False
        self.metrics.start(mode)
        self.event('request_start')

    def event(self, event, *, stage=None, status=None):
        # Fixed schema/allowlist: callers cannot pass arbitrary metadata or text.
        logger.info(json.dumps({
            'schema_version': 1, 'event': event, 'request_id': self.request_id,
            'timestamp_utc': utc_now(), 'runtime_mode': self.mode,
            'stage': stage, 'status': status,
            'candidate_count': self.candidate_count,
            'reranking_state': self.reranking_state,
            'fallback_categories': sorted(self.fallbacks),
            'error_categories': sorted(self.errors),
            'timings_ms': dict(self.timings),
        }, sort_keys=True))

    @contextmanager
    def bind(self):
        token = _active.set(self)
        try:
            yield self
        finally:
            _active.reset(token)

    @contextmanager
    def stage(self, name):
        if name not in STAGES:
            raise ValueError('unknown RAG stage')
        started = time.perf_counter()
        errors_before = self.error_occurrences
        self.event('stage_start', stage=name)
        status = 'completed'
        try:
            yield
        except GeneratorExit:
            status = 'interrupted'
            raise
        except BaseException:
            status = 'failed'
            raise
        finally:
            elapsed = (time.perf_counter() - started) * 1000
            if status == 'completed' and self.error_occurrences != errors_before:
                status = 'failed'
            previous = self.timings[name]
            self.timings[name] = elapsed if previous is None else previous + elapsed
            self.event('stage_end', stage=name, status=status)

    def error(self, category):
        if category not in ERRORS:
            raise ValueError('unknown RAG error category')
        self.errors.add(category)
        self.error_occurrences += 1
        self.event('error')

    def fail(self, category):
        if category not in self.errors:
            self.error(category)
        self.outcome = 'failure'

    def fallback(self, category):
        if category not in FALLBACKS:
            raise ValueError('unknown RAG fallback category')
        self.fallbacks.add(category)
        self.event('fallback')

    def rerank(self, state):
        if state not in RERANK_STATES:
            raise ValueError('unknown RAG reranking state')
        self.reranking_state = state
        self.event('reranking')

    def candidates(self, count):
        self.candidate_count = count
        self.event('candidates')

    def first_content(self):
        if self.timings['streaming_ttft'] is None:
            self.timings['streaming_ttft'] = (time.perf_counter() - self.started) * 1000
            self.event('first_content')

    def stream_done(self):
        self.stream_completed = True
        self.timings['streaming_completion'] = (time.perf_counter() - self.started) * 1000
        self.event('stream_completion')

    def finish(self):
        if self.finished:
            return
        if self.outcome is None:
            if self.mode == 'streaming' and not self.stream_completed:
                self.error('streaming_interruption')
                self.outcome = 'interrupted'
            else:
                self.outcome = 'success'
        self.timings['total'] = (time.perf_counter() - self.started) * 1000
        self.finished = True
        self.metrics.complete(self, self.outcome)
        self.event('request_end', status=self.outcome)


def active_trace():
    return _active.get()


def stage(name):
    trace = active_trace()
    return trace.stage(name) if trace else nullcontext()


def note(method, value):
    trace = active_trace()
    if trace:
        getattr(trace, method)(value)


def timed(name):
    def decorate(function):
        @wraps(function)
        def call(*args, **kwargs):
            with stage(name):
                return function(*args, **kwargs)
        return call
    return decorate


def observe_normal(function):
    @wraps(function)
    def call(*args, **kwargs):
        existing = active_trace()
        trace = existing or RequestTrace('normal')
        try:
            with trace.bind():
                result = function(*args, **kwargs)
            if result.get('error'):
                trace.fail('generation_failure' if result.get('error_code') ==
                           'AI_DEPENDENCY_UNAVAILABLE' else 'application_error')
            return result
        except Exception:
            trace.fail('application_error')
            raise
        finally:
            if existing is None:
                trace.finish()
    return call


def observe_stream(function):
    @wraps(function)
    def stream(*args, **kwargs):
        existing = active_trace()
        trace = existing or RequestTrace('streaming')
        iterator = function(*args, **kwargs)
        try:
            while True:
                # Do not keep a ContextVar bound while yielding to the caller.
                with trace.bind():
                    try:
                        event = next(iterator)
                    except StopIteration:
                        break
                    kind = event.get('type')
                    if kind == 'error':
                        trace.fail('generation_failure' if event.get('code') ==
                                   'AI_DEPENDENCY_UNAVAILABLE' else
                                   ('no_results' if trace.timings['generation'] is None
                                    else 'application_error'))
                    elif kind == 'content' and event.get('data'):
                        trace.first_content()
                    elif kind == 'done':
                        trace.stream_done()
                yield event
        except GeneratorExit:
            raise
        except Exception:
            trace.fail('application_error')
            raise
        finally:
            try:
                with trace.bind():
                    iterator.close()
            finally:
                if existing is None:
                    trace.finish()
    return stream
