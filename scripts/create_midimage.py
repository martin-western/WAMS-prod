from WAMSApp.models import *
import urllib2
from io import BytesIO as StringIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import time

#image_objs = Image.objects.filter(thumbnail=None)
image_objs = Image.objects.all()
size = 128, 128
#print image_objs[0].pk
cnt = 0
error_images = []
for image_obj in image_objs:

    cnt += 1
    print("CNT: ", cnt)
    try:
        infile = str(image_obj.image.url.split("/")[-1])
        print("INFILE", infile)
        thumb = IMage.open(urllib2.urlopen(image_obj.image.url))
        thumb.thumbnail(size)
        print("THUMB", thumb)
        im_type = "JPEG"
        if infile.split(".")[-1].lower()=="png":
            im_type = "PNG" 
        print("im_type", im_type)
        thumb_io = StringIO.BytesIO()
        thumb.save(thumb_io, format=im_type)

        thumb_file = InMemoryUploadedFile(thumb_io, None, infile, 'image/'+im_type, thumb_io.len, None)

        image_obj.thumbnail = thumb_file
        image_obj.save()
        time.sleep(0.1)
    except Exception as e:
        error_images.append(image_obj.pk)

import json
f = open("error_image_pk", "w")
f.write(json.dumps(error_images))
f.close()
