const pushButton = document.getElementById('push')

async function push() {
  let transport = new WebTransport('https://www.localtest.com:4433/wt/test/push')
  await transport.ready;
  console.log('WebTransport Created.')



}
