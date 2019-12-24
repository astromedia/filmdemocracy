import glob
import os

from google.cloud import storage

from django.core.management.base import BaseCommand, CommandError

from filmdemocracy.settings import STATIC_ROOT, GS_STATIC_BUCKET_NAME


class Command(BaseCommand):
    help = 'Upload static files to Google Cloud Storage '

    def upload_local_directory_to_gcs(self, local_path, bucket, gcs_path):
        assert os.path.isdir(local_path)
        local_files = glob.glob(local_path + '/**')
        for local_file in local_files:
            if not os.path.isfile(local_file):
                self.upload_local_directory_to_gcs(local_file, bucket, gcs_path + os.path.basename(local_file) + "/")
            else:
                remote_path = os.path.join(gcs_path, local_file[1 + len(local_path):])
                print(f'  {remote_path}')
                blob = bucket.blob(remote_path)
                blob.upload_from_filename(local_file)

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        self.stdout.write(f'Uploading static files to storage:')
        storage_client = storage.Client()
        storage_static_bucket = storage_client.bucket(GS_STATIC_BUCKET_NAME)
        self.upload_local_directory_to_gcs(STATIC_ROOT, storage_static_bucket, f'static/')
        self.stdout.write(f'  OK')
