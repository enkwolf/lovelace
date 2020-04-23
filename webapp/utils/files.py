import magic
import os

from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.http import HttpResponse


PRIVATE_UPLOAD = getattr(settings, "PRIVATE_STORAGE_FS_PATH", settings.MEDIA_ROOT)

upload_storage = FileSystemStorage(location=PRIVATE_UPLOAD)

def generate_download_response(fs_path, dl_name=None):

    if getattr(settings, "PRIVATE_STORAGE_X_SENDFILE", False):
        response = HttpResponse()
        response["X-Sendfile"] = fs_path.encode("utf-8")
    else:
        with open(fs_path.encode("utf-8"), "rb") as f:
            response = HttpResponse(f.read())
            
    if dl_name:
        dl_name = dl_name
    else:
        dl_name = os.path.basename(fs_path)
        
    mime = magic.Magic(mime=True)    
    response["Content-Type"] = mime.from_file(fs_path)
    response["Content-Disposition"] = "attachment; filename={}".format(dl_name)
    
    return response
    
def get_file_contents(model_instance):
    file_contents = None
    with open(model_instance.fileinfo.path, 'rb') as f:
        file_contents = f.read()
    return file_contents

def get_testfile_path(instance, filename):
    return os.path.join(
        "{exercise_name}_files".format(exercise_name=instance.exercise.name),
        "{filename}".format(filename=filename), # TODO: Versioning?
        # TODO: Language?
    )

