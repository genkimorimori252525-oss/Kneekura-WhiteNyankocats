"""Real local persistence across process restarts; no game or server data."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PcBootAuthorityJvmTests(unittest.TestCase):
    def test_nonce_signature_json_and_foreign_identity_rejection(self):
        javac, java = shutil.which('javac'), shutil.which('java')
        if not javac or not java:
            self.skipTest('JDK unavailable')
        try:
            from Crypto.PublicKey import RSA
        except ImportError:
            self.skipTest('existing RSA tooling unavailable')
        import hashlib
        key = RSA.generate(4096)
        fingerprint = hashlib.sha256(key.public_key().export_key('DER')).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / 'state'
            state.mkdir()
            (state / 'kneekura-local-signing-v1.pk8').write_bytes(key.export_key('DER', pkcs=8))
            source = root / 'KneekuraPcBootAuthority.java'
            source.write_text((ROOT / 'bridge/java/KneekuraPcBootAuthority.java.in').read_text(
                encoding='utf-8').replace('__KNEEKURA_PACKAGE__', 'synthetic').replace(
                    '__KNEEKURA_PC_BOOT_PUBLIC_KEY_SHA256__', fingerprint), encoding='utf-8')
            harness = root / 'SignedHarness.java'
            harness.write_text(r'''package synthetic;
import java.io.File;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.*;
import java.security.spec.*;
import java.util.Base64;
public class SignedHarness {
 static ByteBuffer body(String s) {return ByteBuffer.wrap(s.getBytes(StandardCharsets.UTF_8));}
 public static void main(String[] args) throws Exception {
  File files=new File(args[0]); String id=KneekuraPcBootAuthority.player(files);
  if(!KneekuraPcBootAuthority.available(files))throw new AssertionError("own authority unavailable");
  String request="{\"accountCode\":\""+id+"\",\"nonce\":\"synthetic-nonce\",\"clientInfo\":{\"version\":1}}";
  KneekuraPcBootAuthority.SignedResponse response=KneekuraPcBootAuthority.signedRegistration(body(request),files);
  if(!response.body.contains("\"nonce\":\"synthetic-nonce\""))throw new AssertionError("nonce not echoed");
  Signature verifier=Signature.getInstance("SHA256withRSA");
  verifier.initVerify(KeyFactory.getInstance("RSA").generatePublic(new X509EncodedKeySpec(Files.readAllBytes(new File(args[1]).toPath()))));
  verifier.update(response.body.getBytes(StandardCharsets.UTF_8));
  if(!verifier.verify(Base64.getDecoder().decode(response.signature)))throw new AssertionError("signature invalid");
  verifier.update((response.body+" ").getBytes(StandardCharsets.UTF_8));
  if(verifier.verify(Base64.getDecoder().decode(response.signature)))throw new AssertionError("tampering accepted");
  java.net.URL url=new java.net.URL("https://nyanko-auth.ponosgames.com/v1/users");
  String credentials=KneekuraPcBootAuthority.registration(files);
  java.util.regex.Matcher password=java.util.regex.Pattern.compile("\"password\":\"([^\"]+)\"").matcher(credentials);
  if(!password.find())throw new AssertionError();
  java.util.regex.Matcher refresh=java.util.regex.Pattern.compile("\"passwordRefreshToken\":\"([^\"]+)\"").matcher(credentials);
  if(!refresh.find())throw new AssertionError();
  String refreshRequest="{\"accountCode\":\""+id+"\",\"nonce\":\"refresh-nonce\",\"passwordRefreshToken\":\""+refresh.group(1)+"\"}";
  java.net.URL refreshUrl=new java.net.URL("https://nyanko-auth.ponosgames.com/v1/user/password");
  if(!"refresh-password".equals(KneekuraPcBootAuthority.authOperation("POST",refreshUrl,body(refreshRequest),files)))throw new AssertionError("local refresh unavailable");
  KneekuraPcBootAuthority.SignedResponse renewed=KneekuraPcBootAuthority.signedPasswordRefresh(body(refreshRequest),files);
  verifier.update(renewed.body.getBytes(StandardCharsets.UTF_8));
  if(!verifier.verify(Base64.getDecoder().decode(renewed.signature)))throw new AssertionError("refresh signature invalid");
  if(!renewed.body.contains("\"nonce\":\"refresh-nonce\"") || !renewed.body.contains(password.group(1)) || !renewed.body.contains(refresh.group(1)))throw new AssertionError("refresh contract invalid");
  if(!credentials.equals(KneekuraPcBootAuthority.registration(files)))throw new AssertionError("refresh changed stable local credentials");
  for(String invalid:new String[]{refreshRequest.replace(id,"foreign"),refreshRequest.replace(refresh.group(1),"foreign"),refreshRequest.replace("refresh-nonce",""),refreshRequest+"junk",refreshRequest.replace("\"nonce\":","\"extra\":0,\"nonce\":"),refreshRequest.replace("\"nonce\":","\"nonce\":\"duplicate\",\"nonce\":")}) {
   if(!"other".equals(KneekuraPcBootAuthority.authOperation("POST",refreshUrl,body(invalid),files)))throw new AssertionError("invalid refresh accepted");
   boolean refused=false;
   try{KneekuraPcBootAuthority.signedPasswordRefresh(body(invalid),files);}catch(java.io.IOException expected){refused=true;}
   if(!refused)throw new AssertionError("direct invalid refresh accepted");
  }
  for(String endpoint:new String[]{"http://nyanko-auth.ponosgames.com/v1/user/password","https://foreign.invalid/v1/user/password","https://nyanko-auth.ponosgames.com:444/v1/user/password","https://nyanko-auth.ponosgames.com/v1/user/password?x=1","https://nyanko-auth.ponosgames.com/v1/user/password#x","https://x@nyanko-auth.ponosgames.com/v1/user/password"})
   if(!"other".equals(KneekuraPcBootAuthority.authOperation("POST",new java.net.URL(endpoint),body(refreshRequest),files)))throw new AssertionError("invalid refresh envelope accepted");
  if(!"other".equals(KneekuraPcBootAuthority.authOperation("GET",refreshUrl,body(refreshRequest),files)))throw new AssertionError("invalid refresh method accepted");
  String tokenRequest=request.substring(0,request.length()-1)+",\"password\":\""+password.group(1)+"\"}";
  java.net.URL tokenUrl=new java.net.URL("https://nyanko-auth.ponosgames.com/v1/tokens");
  if(!"tokens".equals(KneekuraPcBootAuthority.authOperation("POST",tokenUrl,body(tokenRequest),files)))throw new AssertionError();
  KneekuraPcBootAuthority.SignedResponse issued=KneekuraPcBootAuthority.signedTokens(body(tokenRequest),files);
  java.util.regex.Matcher token=java.util.regex.Pattern.compile("\"token\":\"([^\"]+)\"").matcher(issued.body);
  if(!token.find())throw new AssertionError();
  String[] jwt=token.group(1).split("\\.");
  if(jwt.length!=3)throw new AssertionError();
  verifier.update((jwt[0]+"."+jwt[1]).getBytes(StandardCharsets.UTF_8));
  if(!verifier.verify(Base64.getUrlDecoder().decode(jwt[2])))throw new AssertionError("local JWT invalid");
  String claims=new String(Base64.getUrlDecoder().decode(jwt[1]),StandardCharsets.UTF_8);
  if(!claims.contains("\"iss\":\"kneekura-local\"") || !claims.contains(id) || !claims.contains("\"exp\":"))throw new AssertionError();
  java.util.HashMap<String,String> managedHeaders=new java.util.HashMap<>();
  managedHeaders.put("Authorization","Bearer "+token.group(1));
  String managedRequest="{\"nonce\":\"managed-nonce\",\"isPaid\":false,\"catfoodAmount\":50,\"rareTicketAmount\":0,\"platinumTicketAmount\":0,\"legendTicketAmount\":0}";
  java.net.URL managedUrl=new java.net.URL("https://nyanko-managed-item.ponosgames.com/v1/managed-items");
  if(!"bootstrap-unpaid".equals(KneekuraPcBootAuthority.managedDiagnostic(body(managedRequest),files,managedHeaders)))throw new AssertionError();
  if(!"token-invalid".equals(KneekuraPcBootAuthority.managedDiagnostic(body(managedRequest),files,new java.util.HashMap<>())))throw new AssertionError();
  if(!"paid-true".equals(KneekuraPcBootAuthority.managedDiagnostic(body(managedRequest.replace("false","true")),files,managedHeaders)))throw new AssertionError();
  if(!"managed-bootstrap".equals(KneekuraPcBootAuthority.authOperation("POST",managedUrl,body(managedRequest),files,managedHeaders)))throw new AssertionError();
  KneekuraPcBootAuthority.SignedResponse managed=KneekuraPcBootAuthority.signedManagedBootstrap(body(managedRequest),files,managedHeaders);
  verifier.update(managed.body.getBytes(StandardCharsets.UTF_8));
  if(!verifier.verify(Base64.getDecoder().decode(managed.signature)))throw new AssertionError();
  File ledger=new File(files,"kneekura-local-managed-v2.record");
  String ledgerBefore=Files.readString(ledger.toPath());
  if(!ledgerBefore.contains("catfoodAmount=50\n"))throw new AssertionError("local inventory not persisted");
  KneekuraPcBootAuthority.signedManagedBootstrap(body(managedRequest),files,managedHeaders);
  if(!ledgerBefore.equals(Files.readString(ledger.toPath())))throw new AssertionError("same snapshot changed");
  for(String amount:new String[]{"-1","2147483648","1.5","true","[]","\"50\""})
    if(!"other".equals(KneekuraPcBootAuthority.authOperation("POST",managedUrl,body(managedRequest.replace("\"catfoodAmount\":50","\"catfoodAmount\":"+amount)),files,managedHeaders)))throw new AssertionError("invalid amount accepted");
  KneekuraPcBootAuthority.signedManagedBootstrap(body(managedRequest.replace("\"catfoodAmount\":50","\"catfoodAmount\":51")),files,managedHeaders);
  String ledgerChanged=Files.readString(ledger.toPath());
  if(!ledgerChanged.contains("catfoodAmount=51\n") || ledgerBefore.equals(ledgerChanged))throw new AssertionError("authenticated snapshot not persisted");
  KneekuraPcBootAuthority.signedManagedBootstrap(body(managedRequest),files,managedHeaders);
  if(!ledgerBefore.equals(Files.readString(ledger.toPath())))throw new AssertionError("decreased snapshot not persisted");
  Files.writeString(ledger.toPath(),ledgerBefore.replace("catfoodAmount=50","catfoodAmount=60"));
  boolean corruptedRejected=false;
  try{KneekuraPcBootAuthority.signedManagedBootstrap(body(managedRequest),files,managedHeaders);}catch(java.io.IOException expected){corruptedRejected=true;}
  if(!corruptedRejected || !Files.readString(ledger.toPath()).contains("catfoodAmount=60\n"))throw new AssertionError("corrupt ledger overwritten");
  Files.writeString(ledger.toPath(),ledgerBefore);
  if(!"other".equals(KneekuraPcBootAuthority.authOperation("POST",managedUrl,body(managedRequest),files,new java.util.HashMap<>())))throw new AssertionError("missing authentication accepted");
  if(!"other".equals(KneekuraPcBootAuthority.authOperation("POST",managedUrl,body(managedRequest.replace("false","true")),files,managedHeaders)))throw new AssertionError("unsupported paid update accepted");
  for(String type:new String[]{"[]","{}","0","null"})
    if(!"other".equals(KneekuraPcBootAuthority.authOperation("POST",managedUrl,body(managedRequest.replace("false",type)),files,managedHeaders)))throw new AssertionError("wrong paid type accepted");
  String foreignPassword=tokenRequest.replace(password.group(1),"foreign");
  if(!"other".equals(KneekuraPcBootAuthority.authOperation("POST",tokenUrl,body(foreignPassword),files)))throw new AssertionError("foreign password accepted");
  for(String invalid:new String[]{request+"junk",request.replace("synthetic-nonce", ""),
   "{\"accountCode\":\""+id+"\",\"accountCode\":\""+id+"\",\"nonce\":\"n\"}",
   "{\"nested\":{\"accountCode\":\""+id+"\"},\"nonce\":\"n\"}",
   request.replace(id,"foreign"),"["+request+"]", request.substring(0,request.length()-1)}) {
   if(KneekuraPcBootAuthority.registrationMatches("POST",url,body(invalid),files))throw new AssertionError("invalid JSON or identity accepted");
  }
  Files.write(new File(files,"kneekura-local-signing-v1.pk8").toPath(),KeyPairGenerator.getInstance("RSA").generateKeyPair().getPrivate().getEncoded());
  boolean rejectedKey=false;
  try {KneekuraPcBootAuthority.signedRegistration(body(request),files);}catch(java.io.IOException expected){rejectedKey=true;}
  if(!rejectedKey)throw new AssertionError("foreign signing key accepted");
  if(KneekuraPcBootAuthority.available(files))throw new AssertionError("foreign authority ready");
  System.out.println("SIGNED_LOCAL_NONCE_INTEGRITY_PASS");
 }
}''', encoding='utf-8')
            public = root / 'public.der'
            public.write_bytes(key.public_key().export_key('DER'))
            result = subprocess.run([javac, '-d', str(root), str(source), str(harness)], capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([java, '-cp', str(root), 'synthetic.SignedHarness', str(state), str(public)], capture_output=True, text=True, timeout=25)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), 'SIGNED_LOCAL_NONCE_INTEGRITY_PASS')

    def test_bridge_boot_authority_requires_explicit_pc_gate(self):
        from tools.base_mod.inject_java_http_bridge import render_bridge_source
        template = (ROOT / 'bridge/java/MyActivity.java.in').read_text(encoding='utf-8')
        default = render_bridge_source(template, flavor='local-research', enabled=False)
        self.assertNotIn('KneekuraPcBootAuthority.payload(', default)
        chosen = render_bridge_source(template, flavor='local-research', enabled=False,
                                      pc_jni_scene_observer=True, pc_boot_authority=True,
                                      offline_393_import_enabled=True)
        self.assertIn('KneekuraPcBootAuthority.payload(', chosen)
        for fields in (dict(flavor='personal'), dict(pc_jni_scene_observer=False),
                       dict(offline_393_import_enabled=False), dict(virgin_save_trial=True)):
            parameters = dict(flavor='local-research', enabled=False, pc_jni_scene_observer=True,
                              pc_boot_authority=True, offline_393_import_enabled=True)
            parameters.update(fields)
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                render_bridge_source(template, **parameters)

    def test_identity_restart_corruption_and_local_origin(self):
        javac, java = shutil.which('javac'), shutil.which('java')
        if not javac or not java:
            self.skipTest('JDK unavailable')
        template = ROOT / 'bridge/java/KneekuraPcBootAuthority.java.in'
        self.assertTrue(template.is_file(), 'local authority implementation missing')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'KneekuraPcBootAuthority.java'
            source.write_text(template.read_text(encoding='utf-8').replace('__KNEEKURA_PACKAGE__', 'synthetic'), encoding='utf-8')
            harness = root / 'Harness.java'
            harness.write_text('''package synthetic;
import java.io.File;
public class Harness {
  public static void main(String[] args) throws Exception {
    String id = KneekuraPcBootAuthority.player(new File(args[0]));
    if (!id.matches("kneekura-local-[0-9a-f]{32}")) throw new AssertionError();
    String registration = KneekuraPcBootAuthority.registration(new File(args[0]));
    if (!registration.contains("\\\"authority\\\":\\\"kneekura-local\\\"")) throw new AssertionError();
    if (!registration.contains("\\\"accountCode\\\":\\\"" + id + "\\\"")) throw new AssertionError();
    if (!registration.equals(KneekuraPcBootAuthority.registration(new File(args[0])))) throw new AssertionError();
    System.out.println(id);
  }
}''', encoding='utf-8')
            compiled = subprocess.run([javac, '-d', str(root), str(source), str(harness)], capture_output=True, text=True, timeout=45)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            state = root / 'state'
            state.mkdir()
            command = [java, '-cp', str(root), 'synthetic.Harness', str(state)]
            first = subprocess.run(command, capture_output=True, text=True, timeout=15)
            second = subprocess.run(command, capture_output=True, text=True, timeout=15)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.stdout, first.stdout)
            concurrent = root / 'concurrent'
            concurrent.mkdir()
            children = [subprocess.Popen([java, '-cp', str(root), 'synthetic.Harness', str(concurrent)],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(6)]
            results = [child.communicate(timeout=20) for child in children]
            self.assertEqual([child.returncode for child in children], [0] * 6)
            self.assertEqual(len({out for out, _ in results}), 1)
            record = state / 'kneekura-local-boot-v1.record'
            self.assertTrue(record.is_file())
            record.write_bytes(b'corrupt')
            broken = subprocess.run(command, capture_output=True, text=True, timeout=15)
            self.assertNotEqual(broken.returncode, 0)
            self.assertEqual(record.read_bytes(), b'corrupt')
            self.assertNotIn(first.stdout.strip(), broken.stderr)


if __name__ == '__main__':
    unittest.main()
