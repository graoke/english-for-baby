/**
 * 轻量级 SRP-6a 客户端实现
 * 用于 PIN 认证，不依赖外部库
 */

// RFC 5054 默认参数（1024-bit）
const N_HEX = 'FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1' +
              '29024E088A67CC74020BBEA63B139B22514A08798E3404DDEF' +
              '9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245E485' +
              'B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386B' +
              'FB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8' +
              'A163BF0598DA48361C55D39A69163FA8FD24CF5F83655D23DC' +
              'A3AD961C62F356208552BB9ED529077096966D670C354E4ABC' +
              '9804F1746C08CA237327FFFFFFFFFFFFFFFF';

const G_HEX = '2';

function hexToBytes(hex: string): Uint8Array {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.substr(i, 2), 16);
  }
  return bytes;
}

function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes).map(b => b.toString(16).padStart(2, '0')).join('');
}

function bigIntToHex(n: bigint): string {
  if (n === 0n) return '0';
  return n.toString(16);
}

function hexToBigInt(hex: string): bigint {
  return BigInt('0x' + hex);
}

// SHA-256（使用 Web Crypto API）
async function sha256(data: Uint8Array): Promise<Uint8Array> {
  const hash = await crypto.subtle.digest('SHA-256', data);
  return new Uint8Array(hash);
}

// SHA-256 多参数版本
async function sha256Multi(...args: Uint8Array[]): Promise<Uint8Array> {
  const totalLength = args.reduce((acc, arr) => acc + arr.length, 0);
  const combined = new Uint8Array(totalLength);
  let offset = 0;
  for (const arr of args) {
    combined.set(arr, offset);
    offset += arr.length;
  }
  return sha256(combined);
}

// 模幂运算（用于小指数）
async function modPow(base: bigint, exp: bigint, mod: bigint): Promise<bigint> {
  let result = 1n;
  base = base % mod;
  while (exp > 0n) {
    if (exp % 2n === 1n) {
      result = (result * base) % mod;
    }
    exp = exp / 2n;
    base = (base * base) % mod;
  }
  return result;
}

// 生成随机字节
function randomBytes(length: number): Uint8Array {
  return crypto.getRandomValues(new Uint8Array(length));
}

// 主类
export class SRPClient {
  private N: bigint;
  private g: bigint;
  private username: string = 'parent';
  private password: string = '';
  private a: bigint = 0n;
  private A: bigint = 0n;
  private salt: Uint8Array = new Uint8Array();
  private B: bigint = 0n;
  private sessionKey: Uint8Array = new Uint8Array();
  
  constructor() {
    this.N = hexToBigInt(N_HEX);
    this.g = hexToBigInt(G_HEX);
  }
  
  // 设置密码
  setPassword(password: string) {
    this.password = password;
  }
  
  // 第一步：生成 A
  async startAuthentication(): Promise<string> {
    // 生成随机 a
    const aBytes = randomBytes(32);
    this.a = BigInt('0x' + bytesToHex(aBytes)) % (this.N - 1n);
    
    // 计算 A = g^a mod N
    this.A = await modPow(this.g, this.a, this.N);
    
    return bigIntToHex(this.A);
  }
  
  // 第二步：处理挑战，生成 M
  async processChallenge(saltHex: string, BHex: string): Promise<string> {
    this.salt = hexToBytes(saltHex);
    this.B = hexToBigInt(BHex);
    
    // 验证 B != 0
    if (this.B === 0n) {
      throw new Error('Invalid B');
    }
    
    // 计算 k = H(N | g)
    const NBytes = hexToBytes(N_HEX);
    const GBytes = hexToBytes(G_HEX);
    const k = await sha256Multi(NBytes, GBytes);
    
    // 计算 x = H(salt | H(':' | password))
    const colonPassword = new TextEncoder().encode(':' + this.password);
    const passwordHash = await sha256(colonPassword);
    const x = await sha256Multi(this.salt, passwordHash);
    const xBigInt = BigInt('0x' + bytesToHex(x));
    
    // 计算 u = H(A | B)
    const ABytes = hexToBytes(bigIntToHex(this.A));
    const BBytes = hexToBytes(bigIntToHex(this.B));
    const u = await sha256Multi(ABytes, BBytes);
    const uBigInt = BigInt('0x' + bytesToHex(u));
    
    // 计算 S = (B - k * g^x)^(a + u * x) mod N
    const gx = await modPow(this.g, xBigInt, this.N);
    const kInt = BigInt('0x' + bytesToHex(k));
    const kgx = (kInt * gx) % this.N;
    const base = (this.B - kgx + this.N) % this.N;
    const exp = (this.a + uBigInt * xBigInt) % (this.N - 1n);
    const S = await modPow(base, exp, this.N);
    
    // 计算 K = H(S)
    const SBytes = hexToBytes(bigIntToHex(S));
    this.sessionKey = await sha256(SBytes);
    
    // 计算 M = H(H(N) ^ H(g) | H(username) | salt | A | B | K)
    const HN = await sha256(NBytes);
    const Hg = await sha256(GBytes);
    
    // XOR H(N) and H(g)
    const HNxorHg = new Uint8Array(32);
    for (let i = 0; i < 32; i++) {
      HNxorHg[i] = HN[i] ^ Hg[i];
    }
    
    const usernameBytes = new TextEncoder().encode(this.username);
    const Husername = await sha256(usernameBytes);
    
    const M = await sha256Multi(HNxorHg, Husername, this.salt, ABytes, BBytes, this.sessionKey);
    
    return bytesToHex(M);
  }
  
  // 第三步：验证服务器
  async verifyServer(HAMKHex: string): Promise<boolean> {
    const HAMK = hexToBytes(HAMKHex);
    const ABytes = hexToBytes(bigIntToHex(this.A));
    
    // 计算 expected HAMK = H(A | M | K)
    const M = await this.computeM();
    const expectedHAMK = await sha256Multi(ABytes, M, this.sessionKey);
    
    // 比较
    if (HAMK.length !== expectedHAMK.length) return false;
    for (let i = 0; i < HAMK.length; i++) {
      if (HAMK[i] !== expectedHAMK[i]) return false;
    }
    return true;
  }
  
  // 辅助：计算 M（用于验证）
  private async computeM(): Promise<Uint8Array> {
    const NBytes = hexToBytes(N_HEX);
    const GBytes = hexToBytes(G_HEX);
    const HN = await sha256(NBytes);
    const Hg = await sha256(GBytes);
    
    const HNxorHg = new Uint8Array(32);
    for (let i = 0; i < 32; i++) {
      HNxorHg[i] = HN[i] ^ Hg[i];
    }
    
    const usernameBytes = new TextEncoder().encode(this.username);
    const Husername = await sha256(usernameBytes);
    
    const ABytes = hexToBytes(bigIntToHex(this.A));
    const BBytes = hexToBytes(bigIntToHex(this.B));
    
    return sha256Multi(HNxorHg, Husername, this.salt, ABytes, BBytes, this.sessionKey);
  }
  
  // 获取 session key
  getSessionKey(): Uint8Array {
    return this.sessionKey;
  }
}
