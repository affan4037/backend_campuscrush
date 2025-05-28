# Setting Up Cloudflare R2 for CampusCrush

This guide walks you through setting up Cloudflare R2 storage for media uploads in the CampusCrush application.

## What is Cloudflare R2?

Cloudflare R2 is an S3-compatible storage service that allows you to store large amounts of unstructured data without the egress fees typically associated with cloud storage services. It's perfect for storing user-uploaded media like images and videos.

## Setup Steps

1. **Create a Cloudflare account** if you don't already have one.

2. **Create an R2 Bucket**:
   - Go to the Cloudflare dashboard
   - Navigate to R2 (under Storage)
   - Click "Create bucket"
   - Name it `campuscrush-media` (or your preferred name)
   - Set up CORS configuration if needed (typically needed for direct uploads from frontend)

3. **Create API Tokens**:
   - Navigate to your bucket settings
   - Go to "API Tokens"
   - Create a new token with Read & Write permissions
   - Save the Access Key ID and Secret Access Key securely

4. **Configure Public Access** (Optional but recommended):
   - In your bucket settings, enable public access if you want the uploaded media to be directly accessible via a URL
   - Alternatively, you can set up a Custom Domain for your R2 bucket

5. **Update Environment Variables**:
   - Add the following to your `.env` file with your actual credentials:
   ```
   # Cloudflare R2 Configuration
   R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
   R2_ACCESS_KEY_ID=your_r2_access_key_id
   R2_SECRET_ACCESS_KEY=your_r2_secret_access_key
   R2_BUCKET_NAME=campuscrush-media
   R2_PUBLIC_URL=https://pub-<id>.r2.dev
   ```

6. **Test the Configuration**:
   - Start your application
   - Attempt to upload media through the application interface
   - Check if the media is properly stored in R2 and accessible

7. **Migrate Existing Media** (If Applicable):
   - Once the configuration is working, run the migration script to move existing files to R2:
   ```
   cd backend_campuscrush
   python migrate_to_r2.py
   ```

## Troubleshooting

- **Connection Issues**: Ensure your R2_ENDPOINT includes your account ID correctly
- **Upload Failures**: Check that your API credentials have the correct permissions
- **Public Access Problems**: Verify that your bucket has proper public access settings if you're using R2_PUBLIC_URL

## Security Considerations

- Never commit your R2 credentials to version control
- Consider using IAM policies to restrict access further if needed
- Implement proper file validation before uploading to prevent malicious files

## Resources

- [Cloudflare R2 Documentation](https://developers.cloudflare.com/r2/)
- [boto3 S3 Client Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html)