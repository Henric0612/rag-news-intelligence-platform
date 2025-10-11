/**
 * E2E测试数据准备脚本
 * 在运行E2E测试前，创建必要的测试账号
 */

import http from 'http'

const createTestUser = (username, email, password) => {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({
      username,
      email,
      password
    })

    const options = {
      hostname: 'localhost',
      port: 5000,
      path: '/api/auth/register',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      }
    }

    const req = http.request(options, (res) => {
      let data = ''

      res.on('data', (chunk) => {
        data += chunk
      })

      res.on('end', () => {
        if (res.statusCode === 201 || res.statusCode === 200) {
          resolve({ success: true, username, statusCode: res.statusCode })
        } else if (res.statusCode === 400 || res.statusCode === 409) {
          // 用户已存在，也算成功
          resolve({ success: true, username, statusCode: res.statusCode, message: '用户已存在' })
        } else {
          resolve({ success: false, username, statusCode: res.statusCode, data })
        }
      })
    })

    req.on('error', (error) => {
      reject({ success: false, username, error: error.message })
    })

    req.setTimeout(5000, () => {
      req.destroy()
      reject({ success: false, username, error: 'Timeout' })
    })

    req.write(postData)
    req.end()
  })
}

const main = async () => {
  console.log('🔧 准备E2E测试数据...\n')

  // 测试账号列表
  const testUsers = [
    { username: 'testuser', email: 'testuser@example.com', password: 'Test123456!' },
    { username: 'admin', email: 'admin@example.com', password: 'admin123' },
    { username: 'test', email: 'test@example.com', password: 'test123' }
  ]

  let successCount = 0
  let failCount = 0

  for (const user of testUsers) {
    try {
      const result = await createTestUser(user.username, user.email, user.password)
      if (result.success) {
        if (result.message) {
          console.log(`✅ ${user.username} - ${result.message}`)
        } else {
          console.log(`✅ ${user.username} - 创建成功`)
        }
        successCount++
      } else {
        console.log(`❌ ${user.username} - 创建失败 (状态码: ${result.statusCode})`)
        failCount++
      }
    } catch (error) {
      console.log(`❌ ${user.username} - 错误: ${error.error || error.message}`)
      failCount++
    }
  }

  console.log(`\n📊 总计: ${successCount} 成功, ${failCount} 失败`)

  if (failCount > 0 && successCount === 0) {
    console.log('\n⚠️  所有测试账号创建失败，请检查后端服务是否运行')
    process.exit(1)
  } else {
    console.log('\n✨ 测试数据准备完成，可以开始E2E测试！')
    process.exit(0)
  }
}

main()

