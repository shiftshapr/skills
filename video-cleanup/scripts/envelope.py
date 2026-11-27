import sys, subprocess, numpy as np
wav=sys.argv[1]; raw=subprocess.run(['ffmpeg','-v','error','-i',wav,'-f','f32le','-ac','1','-ar','16000','-'],capture_output=True).stdout
a=np.frombuffer(raw,np.float32)
for rng in sys.argv[2:]:
    s,e=map(float,rng.split(':')); out=[]
    for t in np.arange(s,e,0.02):
        x=a[int(t*16000):int((t+0.02)*16000)]; db=20*np.log10(np.sqrt((x**2).mean())+1e-9)
        out.append('%.2f:%d'%(t,db))
    print(rng,' '.join(out)); print()
