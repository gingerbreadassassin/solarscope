# solarscope
Just the really rough code to set up my RPi HQ Camera to look through my Lunt LS50THa

![image](https://raw.githubusercontent.com/gingerbreadassassin/solarscope/main/img/PXL_20231003_205018765.jpg)


I originally wanted to try this ⁠with [indi-rpicam](https://github.com/indilib/indi-3rdparty/tree/master/indi-rpicam), but it's broken on bullseye raspbian and no longer being maintained in favor of [indi-libcamera](https://github.com/indilib/indi-3rdparty/tree/master/indi-libcamera)... but 
> It is still under heavy development and not ready for production.

so I knocked together a super rough web ui using rpicamera2, which is bundled in the latest raspbian:
![image](https://github.com/gingerbreadassassin/solarscope/assets/8867180/72505f06-dcae-4015-8ec6-c404c6679ab5)

The pi hq camera together with a pi4 is capable of streaming half resolution at 40fps, so I use that to tune the image. saving an image stops the mjpeg stream and captures a full resolution image
I think my next task here is gonna be to implement some opencv to combine the "surface" and "prominence" images:
![image](https://raw.githubusercontent.com/gingerbreadassassin/solarscope/main/img/surface.png)
![image](https://raw.githubusercontent.com/gingerbreadassassin/solarscope/main/img/prominence.png)
