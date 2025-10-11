/**
 * E2E测试前置检查脚本
 * 检查前端和后端服务是否正在运行
 */

import http from 'http'

const checkService = (host, port, name) => {
  return new Promise((resolve) => {
    const req = http.get(`http://${host}:${port}`, (res) => {
      resolve({ name, running: true, status: res.statusCode })
    })
    
    req.on('error', () => {
      resolve({ name, running: false })
    })
    
    req.setTimeout(2000, () => {
      req.destroy()
      resolve({ name, running: false })
    })
  })
}

const main = async () => {
  console.log('🔍 检查E2E测试所需服务...\n')
  
  const frontend = await checkService('localhost', 3000, '前端服务')
  const backend = await checkService('localhost', 5000, '后端服务')
  
  console.log(`${frontend.running ? '✅' : '❌'} ${frontend.name} (http://localhost:3000)`)
  if (frontend.running) {
    console.log(`   状态码: ${frontend.status}`)
  } else {
    console.log('   请运行: cd Frontend && npm run dev')
  }
  
  console.log(`\n${backend.running ? '✅' : '❌'} ${backend.name} (http://localhost:5000)`)
  if (backend.running) {
    console.log(`   状态码: ${backend.status}`)
  } else {
    console.log('   请运行: cd Backend && python app.py')
  }
  
  if (frontend.running && backend.running) {
    console.log('\n✨ 所有服务正常运行，可以开始E2E测试！')
    console.log('\n运行测试:')
    console.log('  npm run test:e2e          # 运行所有E2E测试')
    console.log('  npm run test:e2e:ui       # UI模式（推荐）')
    console.log('  npm run test:e2e:headed   # 有头模式')
    process.exit(0)
  } else {
    console.log('\n⚠️  请先启动所有必需的服务')
    process.exit(1)
  }
}

main()

