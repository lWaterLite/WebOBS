const readButton = document.getElementById('read');
const closeButton= document.getElementById('close');
const testButton = document.getElementById('test')

const KEY_FRAME_SIZE = 5;
const HEADER_LENGTH = 28;
const PRE_SIGNAL = 0xFFFFFFFF;
const CHANEL = 1;

let transport, bdsReadable, bdsWritable;

let readLoop = true;


function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function read() {
  transport = new WebTransport('https://www.localtest.com:4433/wt/test/get');
  await transport.ready;
  console.log('WebTransport Created.')

  let bds = await transport.createBidirectionalStream();
  let writer = bds.writable.getWriter();
  let reader = bds.readable.getReader();
  let data = new Uint8Array(4).fill(0xFF);
  await writer.write(data);
  console.log('write done. receiving...')
  while (true) {
    const {value, done} = await reader.read();
    if (done) break;
    console.log(value);
  }

  // const readableStream = new ReadableStream({
  //   async start(controller) {
  //     while (readLoop) {
  //       let data = new Uint8Array(4).fill(0xFF);
  //       console.log('Generating data...')
  //       controller.enqueue(data);
  //
  //       await sleep(1000);
  //     }
  //   }
  // })
  //
  // const writableStream = new WritableStream({
  //   async write(chunk, controller){
  //     console.log(chunk)
  //     console.log(controller);
  //     let bds = await transport.createBidirectionalStream();
  //     let writer = bds.writable.getWriter();
  //     let reader = bds.readable.getReader();
  //     await writer.ready;
  //     console.log('writing...')
  //     await writer.write(chunk);
  //     console.log('write done. receiving...')
  //     // let receive = await reader.read();
  //     while (true) {
  //       const {value, done} = await reader.read();
  //       if (done) break;
  //       console.log(value);
  //     }
  //     console.log('receive done.')
  //     await reader.cancel();
  //   }
  // })
  //
  // await readableStream.pipeTo(writableStream)

}

async function close() {
  if (transport !== null) {
    transport.close()
    transport.closed
  }
}

async function test() {
  const writableStream = new WritableStream({
    async write(chunk){
      console.log(chunk)
    }
  })
  console.log('ah oh')
  await bdsReadable.pipeTo(writableStream);
}


readButton.addEventListener('click', read);
closeButton.addEventListener('click', close);
// testButton.addEventListener('click', startWebTransport);

