import sys, subprocess, numpy as np, os
from resemblyzer import VoiceEncoder, preprocess_wav
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ff import ffmpeg
FF=ffmpeg()
ref=np.load(sys.argv[1]); enc=VoiceEncoder("cpu",verbose=False)
for f in sys.argv[2:]:
    x=np.frombuffer(subprocess.run([FF,"-v","error","-i",f,"-ac","1","-ar","16000","-f","f32le","-"],capture_output=True).stdout,np.float32)
    w=10*16000; sc=[]
    for i in range(0,len(x)-w,w):
        s=x[i:i+w]
        if np.sqrt((s**2).mean())<0.005: sc.append(np.nan); continue
        sc.append(float(enc.embed_utterance(preprocess_wav(s,source_sr=16000))@ref))
    sc=np.array(sc); v=sc[~np.isnan(sc)]
    print(f"{os.path.basename(f):18s} {len(x)/16000/60:5.1f} min  median {np.median(v):.2f}  >=0.80: {(v>=.8).mean()*100:3.0f}%  <0.70: {(v<.7).mean()*100:3.0f}%  windows:", " ".join("%.0f"%(s*100) if s==s else "--" for s in sc[:40]))
