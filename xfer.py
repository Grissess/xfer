import asyncio
import random

from quart import Quart, make_response, after_this_request, render_template, stream_with_context, request

WORDS = list(filter(None, open('words.txt').read().split()))
NUM_WORDS = 3

RENDEZVOUS = {}

class Rendezvous:
    ALL = {}

    def __init__(self, id, fname, body):
        self.id = id
        self.ALL[id] = self
        self.fname = fname
        self.body = body
        self.complete = asyncio.Future()
        self.changed = asyncio.Condition()
        self.progress = 0

    async def metered(self):
        async for chunk in self.body:
            self.progress += len(chunk)
            yield chunk
            async with self.changed:
                self.changed.notify_all()

    def finish(self):
        self.complete.set_result(None)
        del self.ALL[self.id]

    async def __aiter__(self):
        while True:
            if self.complete.done():
                return
            async with self.changed:
                await self.changed.wait()
            yield self.progress

def make_id():
    for i in range(128):
        i = '-'.join(random.choice(WORDS) for _ in range(NUM_WORDS))
        if i not in RENDEZVOUS:
            return i
    raise TimeoutError('Too many tries')

app = Quart(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1024*1024*1024*1024

@app.route('/')
async def index():
    return await render_template('index.html')

@app.route('/send', methods=['GET', 'POST'])
async def send():
    @stream_with_context
    async def inner():
        myid = make_id()
        yield f'{myid}\n'.encode()
        async for progress in Rendezvous(myid, request.query_string.decode() or 'unnamed', request.body):
            yield str(progress).encode()
        yield 'Success\n'.encode()
    return inner(), 200, {'Content-type': 'text/plain'}

@app.route('/recv/<string:sid>')
async def recv(sid):
    rend = Rendezvous.ALL[sid]
    
    @after_this_request
    async def cleanup(resp):
        rend.finish()
        return resp

    safe_name = rend.fname.replace('"', '\\"')
    return rend.metered(), 200, {
            'Content-type': 'application/octet-stream',
            'Content-disposition': f'attachment; filename="{safe_name}"',
    }

if __name__ == '__main__':
    app.run(debug=True)

