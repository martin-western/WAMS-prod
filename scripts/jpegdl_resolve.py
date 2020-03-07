from WAMSApp.models import *
from PIL import Image as IMage
import urllib
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import time
image_objs = Image.objects.filter(image__icontains=".jpgdl")
cnt = 0
for image_obj in image_objs:
    cnt += 1
    print(cnt)
    infile = str(image_obj.image.url.split("/")[-1])
    infile = infile.replace("jpgdl", "jpg")
    thumb = IMage.open(urllib.request.urlopen(image_obj.image.url))
    im_type = thumb.format
    thumb_io = BytesIO()
    thumb.save(thumb_io, format=im_type)
    thumb_file = InMemoryUploadedFile(thumb_io, None, infile, 'image/'+im_type, thumb_io.getbuffer().nbytes, None)
    image_obj.image = thumb_file
    image_obj.save()
    time.sleep(0.05)
#infile = infile.replace("jpegdl1", "jpeg")