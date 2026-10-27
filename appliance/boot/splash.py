#!/usr/bin/env python3
"""Non-invasive early userspace splash. Never writes to storage or network."""
import fcntl, mmap, os, struct, sys, time
# Simple direct framebuffer animation, 32-bit RGB only. DRM UI starts after it exits.
FBIOGET_VSCREENINFO=0x4600
FBIOGET_FSCREENINFO=0x4602

def main():
    try:
        fd=os.open('/dev/fb0',os.O_RDWR|os.O_CLOEXEC)
        var=bytearray(160); fcntl.ioctl(fd,FBIOGET_VSCREENINFO,var,True)
        x,y,_,_,_,_,bpp=struct.unpack_from('7I',var)
        fix=bytearray(80);fcntl.ioctl(fd,FBIOGET_FSCREENINFO,fix,True)
        stride=struct.unpack_from('I',fix,48)[0]
        if bpp!=32 or x<320 or y<200 or stride<x*4 or stride*y>128*1024*1024:
            os.close(fd);return
        mm=mmap.mmap(fd,stride*y,mmap.MAP_SHARED,mmap.PROT_READ|mmap.PROT_WRITE)
        def rect(a,b,w,h,r,g,bl):
            a=max(0,a); b=max(0,b);w=min(w,x-a);h=min(h,y-b)
            if w<=0 or h<=0:return
            px=bytes((bl,g,r,0xff)); line=px*w
            for yy in range(b,b+h):mm[yy*stride+a*4:yy*stride+(a+w)*4]=line
        # Background and animated progress indicator. Exit when parent stops us.
        rect(0,0,x,y,10,24,36)
        rect(x//6,y//2-70,x*2//3,6,42,131,55)
        rect(x//6,y//2+50,x*2//3,8,28,49,63)
        pos=0
        while True:
            width=x*2//3
            rect(x//6,y//2+50,width,8,28,49,63)
            rect(x//6+(pos%max(1,width-90)),y//2+50,90,8,89,178,234)
            pos+=13
            time.sleep(.08)
    except (OSError,ValueError,OverflowError):
        # No framebuffer: leave boot functional, only graphical effect unavailable.
        return

if __name__=='__main__':main()
