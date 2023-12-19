import { parse, parseExpression } from '@babel/parser';
import { Deobfuscator } from './deobfuscator/deobfuscator';

Bun.serve({
    port: 48777,
    async fetch(req: Request) {
        return new Response(await buildResp(req));
    },
});

async function buildResp(req: Request) {
    try {
        (globalThis as any).parser = { parse, parseExpression };
        const js = await req.text()
        const ast = parse(js, { sourceType: 'unambiguous' });
        const deobfuscator = new Deobfuscator(ast);
        const output = deobfuscator.execute();
        return output        
    } catch (error) {
        return "Invalid input."
    }
}
