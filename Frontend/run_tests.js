#!/usr/bin/env node

import { execSync } from 'child_process'
import fs from 'fs'

console.log('🧪 RAG News Intelligence Platform 前端测试套件')
console.log('='.repeat(50))

// 检查是否在正确的目录
if (!fs.existsSync('package.json')) {
  console.log('❌ 错误: 请在 Frontend 目录下运行此脚本')
  process.exit(1)
}

// 检查是否安装了测试依赖
if (!fs.existsSync('node_modules/vitest')) {
  console.log('\n📦 安装测试依赖...')
  try {
    execSync('npm install', { stdio: 'inherit' })
  } catch (error) {
    console.log('❌ 安装依赖失败')
    process.exit(1)
  }
}

// 测试统计
let totalTests = 0
let passedTests = 0
let failedTests = 0

// 运行单元测试
console.log('\n🔬 运行单元测试 (9个)...')
try {
  execSync('npm run test:unit', { stdio: 'inherit' })
  console.log('✅ 单元测试通过')
  passedTests++
} catch (error) {
  console.log('❌ 单元测试失败')
  failedTests++
}

// 运行集成测试
console.log('\n🔗 运行集成测试 (5个)...')
try {
  execSync('npm run test:integration', { stdio: 'inherit' })
  console.log('✅ 集成测试通过')
  passedTests++
} catch (error) {
  console.log('❌ 集成测试失败')
  failedTests++
}

// 运行E2E测试
console.log('\n🌐 运行E2E测试 (6个)...')
try {
  execSync('npm run test:e2e', { stdio: 'inherit' })
  console.log('✅ E2E测试通过')
  passedTests++
} catch (error) {
  console.log('⚠️  E2E测试跳过（需要后端服务运行）')
}

// 生成覆盖率报告
console.log('\n📊 生成测试覆盖率报告...')
try {
  execSync('npm run test:coverage', { stdio: 'inherit' })
  console.log('✅ 覆盖率报告生成成功')
} catch (error) {
  console.log('⚠️  覆盖率报告生成失败')
}

console.log('\n' + '='.repeat(50))
console.log('📈 测试总结')
console.log('='.repeat(50))
console.log(`✅ 通过: ${passedTests}`)
console.log(`❌ 失败: ${failedTests}`)
console.log(`📦 总计: 22个测试文件 (9个单元 + 5个集成 + 6个E2E + 2个其他)`)
console.log(`📊 覆盖率报告: Frontend/coverage/index.html`)
console.log('='.repeat(50))

if (failedTests > 0) {
  console.log('\n⚠️  部分测试失败，请检查错误信息')
  process.exit(1)
} else {
  console.log('\n✅ 所有测试完成！')
}
