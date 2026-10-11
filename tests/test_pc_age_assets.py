"""Pin private original age resources without shipping their copyrighted bytes."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PcAgeAssetsTests(unittest.TestCase):
    def test_exact_origin_path_query_and_private_file_integrity(self):
        javac, java = shutil.which('javac'), shutil.which('java')
        if not javac or not java:
            self.skipTest('JDK unavailable')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'KneekuraPcAgeAssets.java'
            source.write_text((ROOT / 'bridge/java/KneekuraPcAgeAssets.java.in').read_text(
                encoding='utf-8').replace('__KNEEKURA_PACKAGE__', 'synthetic'), encoding='utf-8')
            harness = root / 'Harness.java'
            harness.write_text('''package synthetic;
import java.io.File;
import java.nio.file.Files;
public class Harness {
 public static void main(String[] args) throws Exception {
  String base="https://ponosgames.com/information/appli/battlecats/age/";
  if(!KneekuraPcAgeAssets.isPage(base+"index.html"))throw new AssertionError();
  for(String bad:new String[]{base+"index.html?unknown=1",base+"%69ndex.html",base+"../age/index.html",base+"gdpr.html",
    base.replace("https:","http:")+"index.html",base.replace("ponosgames.com","ponosgames.com.evil")+"index.html",
    base.replace("ponosgames.com","user@ponosgames.com")+"index.html",base.replace("ponosgames.com","ponosgames.com:444")+"index.html"})
   if(KneekuraPcAgeAssets.isPage(bad))throw new AssertionError("bad page accepted");
  File files=new File(args[0]); File dir=new File(files,"kneekura-local-age-v1");dir.mkdirs();
  if(KneekuraPcAgeAssets.read(files,base+"index.html")!=null)throw new AssertionError("missing accepted");
  Files.write(new File(dir,"index.html").toPath(),"synthetic tampered HTML".getBytes());
  if(KneekuraPcAgeAssets.read(files,base+"index.html")!=null)throw new AssertionError("tampering accepted");
  byte[] synthetic="synthetic pinned HTML".getBytes(java.nio.charset.StandardCharsets.UTF_8);
  StringBuilder digest=new StringBuilder();
  for(byte b:java.security.MessageDigest.getInstance("SHA-256").digest(synthetic))digest.append(String.format("%02x",b&255));
  KneekuraPcAgeAssets.SHA256[0]=digest.toString();
  Files.write(new File(dir,"index.html").toPath(),synthetic);
  if(!java.util.Arrays.equals(synthetic,KneekuraPcAgeAssets.read(files,base+"index.html")))throw new AssertionError("verified private bytes not served");
  Files.write(new File(dir,"index.html").toPath(),"tampered after publication".getBytes());
  if(KneekuraPcAgeAssets.read(files,base+"index.html")!=null)throw new AssertionError("later tampering accepted");
  if(KneekuraPcAgeAssets.read(files,base+"../../../SAVE_DATA")!=null)throw new AssertionError("escape accepted");
  if(KneekuraPcAgeAssets.asset(base+"js/age.js?01")!=3)throw new AssertionError("pinned script not routed");
  if(KneekuraPcAgeAssets.asset(base+"js/age.js?02")!=-1)throw new AssertionError("unknown script accepted");
  if(KneekuraPcAgeAssets.asset(base+"css/reset.css")!=1)throw new AssertionError();
  System.out.println("EXACT_PRIVATE_AGE_ROUTING_PASS");
 }
}''', encoding='utf-8')
            compiled = subprocess.run([javac, '-d', str(root), str(source), str(harness)],
                                      capture_output=True, text=True, timeout=30)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            result = subprocess.run([java, '-cp', str(root), 'synthetic.Harness', str(root / 'files')],
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('EXACT_PRIVATE_AGE_ROUTING_PASS', result.stdout)
