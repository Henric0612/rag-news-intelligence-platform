"""
文件上传相关API路由
"""
import os
import logging
from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename

from Backend.services.file_service import FileService
from Backend.utils.decorators import jwt_required
from Backend.utils.response import success_response, error_response

logger = logging.getLogger(__name__)

# 创建蓝图
upload_bp = Blueprint('upload', __name__, url_prefix='/api/upload')

# 初始化服务
file_service = FileService()


@upload_bp.route('/file', methods=['POST'])
@jwt_required()
def upload_file():
    """上传文件"""
    try:
        # 检查是否有文件
        if 'file' not in request.files:
            return error_response('没有上传文件', 400)
        
        file = request.files['file']
        
        # 检查文件名
        if file.filename == '':
            return error_response('没有选择文件', 400)
        
        # 获取额外参数
        category = request.form.get('category')
        tags_str = request.form.get('tags', '')
        
        # 解析标签
        tags = []
        if tags_str:
            tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
        
        # 处理文件上传
        result = file_service.upload_file(file, category, tags)
        
        if result['success']:
            return success_response({
                'message': '文件上传成功',
                'result': result
            }, 201)
        else:
            return error_response(result['error'], 400)
        
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        return error_response('文件上传失败', 500)


@upload_bp.route('/files', methods=['POST'])
@jwt_required()
def upload_multiple_files():
    """批量上传文件"""
    try:
        # 检查是否有文件
        if 'files' not in request.files:
            return error_response('没有上传文件', 400)
        
        files = request.files.getlist('files')
        
        if not files or files[0].filename == '':
            return error_response('没有选择文件', 400)
        
        # 获取额外参数
        category = request.form.get('category')
        tags_str = request.form.get('tags', '')
        
        # 解析标签
        tags = []
        if tags_str:
            tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
        
        # 批量处理文件
        results = []
        successful_uploads = 0
        failed_uploads = 0
        
        for file in files:
            if file.filename == '':
                continue
            
            result = file_service.upload_file(file, category, tags)
            
            if result['success']:
                successful_uploads += 1
                results.append({
                    'filename': file.filename,
                    'status': 'success',
                    'result': result
                })
            else:
                failed_uploads += 1
                results.append({
                    'filename': file.filename,
                    'status': 'failed',
                    'error': result['error']
                })
        
        return success_response({
            'message': f'批量上传完成，成功 {successful_uploads} 个，失败 {failed_uploads} 个',
            'successful_uploads': successful_uploads,
            'failed_uploads': failed_uploads,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"批量文件上传失败: {str(e)}")
        return error_response('批量文件上传失败', 500)


@upload_bp.route('/validate', methods=['POST'])
@jwt_required()
def validate_file():
    """验证文件（不上传）"""
    try:
        # 检查是否有文件
        if 'file' not in request.files:
            return error_response('没有上传文件', 400)
        
        file = request.files['file']
        
        # 检查文件名
        if file.filename == '':
            return error_response('没有选择文件', 400)
        
        # 验证文件
        validation = file_service.validate_file(file)
        
        if validation['valid']:
            return success_response({
                'message': '文件验证通过',
                'validation': validation
            })
        else:
            return error_response(validation['error'], 400)
        
    except Exception as e:
        logger.error(f"文件验证失败: {str(e)}")
        return error_response('文件验证失败', 500)


@upload_bp.route('/files', methods=['GET'])
@jwt_required()
def get_uploaded_files():
    """获取已上传文件列表"""
    try:
        result = file_service.get_uploaded_files_info()
        
        if result['success']:
            return success_response(result)
        else:
            return error_response(result['error'], 500)
        
    except Exception as e:
        logger.error(f"获取上传文件列表失败: {str(e)}")
        return error_response('获取上传文件列表失败', 500)


@upload_bp.route('/files/<filename>', methods=['DELETE'])
@jwt_required()
def delete_uploaded_file(filename):
    """删除已上传的文件"""
    try:
        # 安全文件名处理
        secure_name = secure_filename(filename)
        
        result = file_service.delete_uploaded_file(secure_name)
        
        if result['success']:
            return success_response({
                'message': '文件删除成功',
                'result': result
            })
        else:
            return error_response(result['error'], 500)
        
    except Exception as e:
        logger.error(f"删除上传文件失败: {str(e)}")
        return error_response('删除上传文件失败', 500)


@upload_bp.route('/supported-formats', methods=['GET'])
def get_supported_formats():
    """获取支持的文件格式"""
    try:
        return success_response({
            'supported_formats': FileService.SUPPORTED_EXTENSIONS,
            'max_file_size': FileService.MAX_FILE_SIZE,
            'max_file_size_mb': FileService.MAX_FILE_SIZE / (1024 * 1024)
        })
        
    except Exception as e:
        logger.error(f"获取支持格式失败: {str(e)}")
        return error_response('获取支持格式失败', 500)


@upload_bp.route('/chunk', methods=['POST'])
@jwt_required()
def chunk_text():
    """文本分块处理"""
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return error_response('缺少文本内容', 400)
        
        text = data['text']
        chunk_size = data.get('chunk_size', 1000)
        overlap = data.get('overlap', 200)
        
        if not text or len(text.strip()) < 10:
            return error_response('文本内容太短', 400)
        
        # 分块处理
        chunks = file_service.chunk_text(text, chunk_size, overlap)
        
        return success_response({
            'message': '文本分块完成',
            'chunks': chunks,
            'chunks_count': len(chunks),
            'original_length': len(text)
        })
        
    except Exception as e:
        logger.error(f"文本分块失败: {str(e)}")
        return error_response('文本分块失败', 500)


@upload_bp.route('/extract', methods=['POST'])
@jwt_required()
def extract_content():
    """提取文件内容（不上传）"""
    try:
        # 检查是否有文件
        if 'file' not in request.files:
            return error_response('没有上传文件', 400)
        
        file = request.files['file']
        
        # 检查文件名
        if file.filename == '':
            return error_response('没有选择文件', 400)
        
        # 验证文件
        validation = file_service.validate_file(file)
        if not validation['valid']:
            return error_response(validation['error'], 400)
        
        # 保存临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=validation['extension']) as temp_file:
            file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        try:
            # 提取内容
            result = file_service.extract_file_content(temp_file_path, validation['extension'])
            
            if result['success']:
                return success_response({
                    'message': '内容提取成功',
                    'content': result['content'],
                    'content_length': result['content_length'],
                    'filename': file.filename
                })
            else:
                return error_response(result['error'], 400)
                
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file_path)
            except:
                pass
        
    except Exception as e:
        logger.error(f"内容提取失败: {str(e)}")
        return error_response('内容提取失败', 500)


@upload_bp.route('/batch-process', methods=['POST'])
@jwt_required()
def batch_process_data():
    """批量处理数据"""
    try:
        data = request.get_json()
        
        if not data:
            return error_response('缺少请求数据', 400)
        
        operation = data.get('operation')
        data_ids = data.get('data_ids', [])
        
        if not operation:
            return error_response('缺少操作类型', 400)
        
        if not data_ids:
            return error_response('没有指定要处理的数据', 400)
        
        # 导入数据服务
        from Backend.services.data_service import DataService
        data_service = DataService()
        
        # 执行批量处理
        result = data_service.batch_process_data(operation, data_ids, **data.get('params', {}))
        
        if result['success']:
            return success_response({
                'message': '批量处理完成',
                'result': result
            })
        else:
            return error_response(result['error'], 500)
        
    except Exception as e:
        logger.error(f"批量处理数据失败: {str(e)}")
        return error_response('批量处理数据失败', 500)


@upload_bp.route('/export', methods=['GET'])
@jwt_required()
def export_data():
    """导出数据"""
    try:
        data_type = request.args.get('data_type', 'all')
        format_type = request.args.get('format', 'json')
        
        # 导入数据服务
        from Backend.services.data_service import DataService
        data_service = DataService()
        
        # 执行导出
        result = data_service.export_data(data_type, format_type)
        
        if result['success']:
            return success_response(result)
        else:
            return error_response(result['error'], 500)
        
    except Exception as e:
        logger.error(f"导出数据失败: {str(e)}")
        return error_response('导出数据失败', 500)
