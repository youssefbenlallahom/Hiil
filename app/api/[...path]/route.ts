import {NextRequest} from 'next/server';

export const runtime='nodejs';
export const dynamic='force-dynamic';
type Context={params:Promise<{path:string[]}>};
async function forward(request:NextRequest,context:Context){
  const {path}=await context.params;
  const origin=process.env.INTERNAL_API_URL||'http://127.0.0.1:8000';
  const url=new URL('/api/'+path.map(encodeURIComponent).join('/'),origin);
  const length=Number(request.headers.get('content-length')||0);
  if(length>13*1024*1024)return Response.json({detail:'Le fichier dépasse la limite de 12 Mo.'},{status:413});
  try{
    const response=await fetch(url,{
      method:request.method,
      headers:request.headers.get('content-type')?{'Content-Type':request.headers.get('content-type')!}:{},
      body:request.method==='GET'?undefined:await request.arrayBuffer(),
      signal:AbortSignal.timeout(240000),cache:'no-store',redirect:'error',
    });
    const headers=new Headers();
    for(const key of ['content-type','content-disposition','x-content-type-options']){
      const value=response.headers.get(key);if(value)headers.set(key,value);
    }
    headers.set('Cache-Control','no-store');
    return new Response(response.body,{status:response.status,headers});
  }catch{
    return Response.json({detail:'Le service de traitement est indisponible ou a dépassé le délai. Vérifiez le backend puis réessayez.'},{status:502});
  }
}
export const GET=forward;
export const POST=forward;
