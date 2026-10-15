import test from 'node:test';
import assert from 'node:assert/strict';
import {beginOperation,pendingOperations,reconcileOperation,sendOperation} from '../lib/operations.ts';
function storage() { const map=new Map(); globalThis.sessionStorage={getItem:k=>map.get(k)||null,setItem:(k,v)=>map.set(k,v)}; }
test('reload recovery preserves each operation key and never resubmits a mutation', async()=>{
  storage(); const original=globalThis.fetch;
  try {
    for(const type of ['upload','retry','chat','delete']) {
      const op=beginOperation(type,7);
      const restored=pendingOperations().find(item=>item.key===op.key);
      assert.deepEqual(restored,op);
      let requests=0;
      globalThis.fetch=async(url,options)=>{requests++;assert.equal(options.method,undefined);assert.ok(url.endsWith(op.key));return Response.json({status:'succeeded',response:{id:7},http_status:200});};
      assert.equal((await reconcileOperation(restored)).status,'succeeded');
      assert.equal(requests,1);assert.equal(pendingOperations().length,0);
    }
  } finally {globalThis.fetch=original;}
});
test('uncertain expired network response keeps the key and blocks a new implicit request',async()=>{
  storage();const original=globalThis.fetch;
  try {const op=beginOperation('chat');op.deadlineAt=Date.now()-1;globalThis.fetch=async()=>{throw new Error('offline');};assert.equal(await reconcileOperation(op),null);assert.equal(pendingOperations()[0].key,op.key);}
  finally {globalThis.fetch=original;}
});
test('server rejection finishes the original operation and exposes request ID',async()=>{
  storage();const original=globalThis.fetch;
  try {const op=beginOperation('upload');globalThis.fetch=async()=>Response.json({code:'invalid_document',detail:'Không hợp lệ'},{status:422,headers:{'X-Request-ID':'trace-123'}});const state=await sendOperation(op,'/upload',{method:'POST'});assert.equal(state.status,'failed');assert.equal(state.response.request_id,'trace-123');assert.equal(pendingOperations().length,0);}
  finally {globalThis.fetch=original;}
});
