import os
import logging

try:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api
    CLOUDINARY_AVAILABLE = True
except ImportError:
    logging.warning("Cloudinary library not installed. Image cloud storage will be disabled.")
    CLOUDINARY_AVAILABLE = False

# Cloudinary Configuration
if CLOUDINARY_AVAILABLE:
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
    api_key = os.environ.get('CLOUDINARY_API_KEY')
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')

    if not all([cloud_name, api_key, api_secret]):
        logging.error("Cloudinary configuration is incomplete. Missing environment variables.")
    else:
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret
        )

def upload_image(file, folder='car_images'):
    """
    Upload an image to Cloudinary
    :param file: File object to upload
    :param folder: Cloudinary folder to store the image
    :return: Cloudinary URL of the uploaded image
    """
    if not CLOUDINARY_AVAILABLE:
        logging.error("Cloudinary is not available. Cannot upload image.")
        return None

    try:
        # Upload the file to Cloudinary
        upload_result = cloudinary.uploader.upload(
            file, 
            folder=folder,
            # Optional: add transformations or other upload options
            transformation=[
                {'width': 800, 'height': 600, 'crop': 'limit'}
            ]
        )
        return upload_result['secure_url']
    except Exception as e:
        logging.error(f"Cloudinary upload error: {e}")
        return None

def delete_image(public_id):
    """
    Delete an image from Cloudinary
    :param public_id: Public ID of the image to delete
    """
    if not CLOUDINARY_AVAILABLE:
        logging.error("Cloudinary is not available. Cannot delete image.")
        return

    try:
        cloudinary.uploader.destroy(public_id)
    except Exception as e:
        logging.error(f"Cloudinary delete error: {e}")
