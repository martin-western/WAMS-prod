from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

import logging
import json
import uuid

from PIL import Image as IMAGE
from PIL import ExifTags
from io import BytesIO
from bs4 import BeautifulSoup

from WAMSApp.models import *
from SalesApp.utils import *
from django.core.cache import cache

logger = logging.getLogger(__name__)

class Image(models.Model):

    description = models.TextField(null=True, blank=True)
    image = models.ImageField(upload_to='')
    thumbnail = models.ImageField(upload_to='thumbnails', null=True, blank=True)
    mid_image = models.ImageField(upload_to='midsize', null=True, blank=True)

    class Meta:
        verbose_name = "Image"
        verbose_name_plural = "Images"

    def __str__(self):
        return str(self.image.url)

    def save(self, *args, **kwargs):
        try:  
            
            def rotate_image(image):
                try:
                    exif=dict(image._getexif().items())
                    orientation = 0
                    for index in ExifTags.TAGS.keys():
                        if ExifTags.TAGS[index] =='Orientation':
                            orientation = index
                            break

                    if orientation!= 0 and exif[orientation] == 6:
                        image = image.rotate(270)
                    elif orientation!= 0 and exif[orientation] == 3:
                        image = image.rotate(180)
                    elif orientation!= 0 and exif[orientation] == 8:
                        image = image.rotate(90)
                    elif orientation!= 0 and exif[orientation] == 2:
                        image = image.transpose(Image.FLIP_LEFT_RIGHT)
                    elif orientation!= 0 and exif[orientation] == 5:
                        image = image.transpose(Image.FLIP_LEFT_RIGHT)
                        image = image.rotate(270)
                    elif orientation!= 0 and exif[orientation] == 4:
                        image = image.transpose(Image.FLIP_LEFT_RIGHT)
                        image = image.rotate(180)
                    elif orientation!= 0 and exif[orientation] == 7:
                        image = image.transpose(Image.FLIP_LEFT_RIGHT)
                        image = image.rotate(90)
                    return image
                except Exception as e:
                    return image

            size = 128, 128
            thumb = IMAGE.open(self.image)
            thumb.thumbnail(size)
            infile = self.image.file.name
            im_type = thumb.format 
            thumb_io = BytesIO()
            thumb = rotate_image(thumb)
            thumb.save(thumb_io, im_type)

            thumb_file = InMemoryUploadedFile(thumb_io, None, infile, 'image/'+im_type, thumb_io.getbuffer().nbytes, None)
            self.thumbnail = thumb_file

            size2 = 512, 512
            thumb2 = IMAGE.open(self.image)
            thumb2.thumbnail(size2)
            thumb_io2 = BytesIO()
            thumb2 = rotate_image(thumb2)
            thumb2.save(thumb_io2, format=im_type)

            thumb_file2 = InMemoryUploadedFile(thumb_io2, None, infile, 'image/'+im_type, thumb_io2.getbuffer().nbytes, None)

            self.mid_image = thumb_file2
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.error("Save Image: %s at %s", e, str(exc_tb.tb_lineno))

        super(Image, self).save(*args, **kwargs)

class SalesAppUser(User):

    image = models.ForeignKey(Image, null=True, blank=True, on_delete=models.CASCADE)
    contact_number = models.CharField(max_length=200, default="",blank=True,null=True)
    designation = models.CharField(max_length=200, default="Content Manager",blank=True,null=True)
    
    def save(self, *args, **kwargs):
        if self.pk == None:
            self.set_password(self.password)
        super(SalesAppUser, self).save(*args, **kwargs)

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "SalesAppUser"
        verbose_name_plural = "SalesAppUser"