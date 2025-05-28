# Cloudflare R2 Setup Guide for CampusCrush

This guide will help you properly configure Cloudflare R2 storage for CampusCrush media files (profile pictures and post media).

## 1. Create a Cloudflare R2 Bucket

1. Log in to your Cloudflare account
2. Navigate to R2 in the sidebar
3. Click "Create bucket"
4. Name the bucket `campuscrush-media` (or any other name you prefer)
5. Click "Create bucket"

## 2. Set up Public Access

For media files to be accessible directly from the frontend, you'll need to configure public access:

1. In your bucket dashboard, go to "Settings" > "Public Access"
2. Enable public access by clicking "Edit" and then "Enable public access"
3. Take note of the public URL (it should be in the format `https://pub-<id>.r2.dev`)

## 3. Create API Tokens

1. In your bucket dashboard, go to "Settings" > "API Tokens"
2. Click "Create API token"
3. Select "R2 Storage" with "Admin" or "Object Read & Write" permissions
4. Limit the token to the specific bucket you created
5. Click "Create API token"
6. Save the Access Key ID and Secret Access Key - you'll need these in your `.env` file

## 4. Configure Environment Variables

Create a `.env` file in the root of the backend directory with the following variables:

```
# Cloudflare R2 Configuration
R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=your_access_key_id
R2_SECRET_ACCESS_KEY=your_secret_access_key
R2_BUCKET_NAME=campuscrush-media
R2_PUBLIC_URL=https://pub-<id>.r2.dev
```

Replace:
- `<account-id>` with your Cloudflare account ID
- `your_access_key_id` with the Access Key ID from step 3
- `your_secret_access_key` with the Secret Access Key from step 3
- `https://pub-<id>.r2.dev` with the public URL from step 2

## 5. Test Your Configuration

Run the test script to verify that your R2 configuration is working correctly:

```
python test_r2_connection.py
```

This script will:
1. Check if all required environment variables are set
2. Test the connection to your R2 bucket
3. Create test files to verify write permissions
4. List objects in the bucket

If the script runs successfully, your R2 configuration is working.

## 6. Migrate Existing Media

If you already have media files stored locally, you can migrate them to R2 with the migration script:

```
python migrate_to_r2.py
```

This will copy all existing files from the local storage to R2.

## Troubleshooting

### No connection to R2

If you see errors like "R2 storage not properly configured" or "Failed to upload to R2":

1. Double-check your environment variables
2. Ensure your Cloudflare account has R2 enabled
3. Verify your API token has the correct permissions
4. Check if your network can access the Cloudflare R2 API

### Media doesn't appear on the frontend

If media uploads successfully but doesn't appear on the frontend:

1. Check if the R2 public URL is correctly configured
2. Verify that your bucket has public access enabled
3. Check the browser console for CORS errors
4. Ensure the frontend is using the correct URL pattern for media

### Mixed Content Errors

If you're getting mixed content errors in the browser:

1. Ensure both your app and R2 are using HTTPS
2. Update the frontend URL patterns to use HTTPS

## Frontend Configuration

The frontend needs to be aware of the R2 storage URLs. Update the media URL patterns in your frontend code to use the R2 public URL for media files. 