const { createServer } = require('https')
const { parse } = require('url')
const next = require('next')
const fs = require('fs')

const dev = true
const app = next({ dev })
const handle = app.getRequestHandler()

const httpsOptions = {
  key: fs.readFileSync('./100.124.146.119+2-key.pem'),
  cert: fs.readFileSync('./100.124.146.119+2.pem'),
}

app.prepare().then(() => {
  createServer(httpsOptions, (req, res) => {
    const parsedUrl = parse(req.url, true)
    handle(req, res, parsedUrl)
  }).listen(3443, () => {
    console.log('> Ready on https://100.124.146.119:3443')
  })
})
