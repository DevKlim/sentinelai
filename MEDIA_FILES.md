# Media Files Note

## Excluded Large Media Files

The following large media files were excluded from this repository due to GitHub's file size limitations:

### EIDO Agent Static Files
- `eido-agent/static/videos/hero_background.mp4` (60MB)
- `eido-agent/static/videos/placeholder_video.mp4`
- `eido-agent/static/images/image1.gif` (2.4MB)
- `eido-agent/static/images/image2.gif` (2.5MB)
- `eido-agent/static/images/image3.gif` (1.9MB)
- `eido-agent/static/images/image4.gif` (5.1MB)
- `eido-agent/static/images/image5.gif` (1.8MB)

## Alternative Solutions

### Option 1: Use Git LFS (Large File Storage)
If you need these files in the repository, you can use Git LFS:

```bash
# Install Git LFS
git lfs install

# Track large media files
git lfs track "*.mp4"
git lfs track "*.gif"

# Add and commit
git add .gitattributes
git add .
git commit -m "Add large media files with Git LFS"
```

### Option 2: Host Media Files Externally
- Upload videos to YouTube/Vimeo and embed them
- Host images on a CDN or image hosting service
- Use placeholder images and provide download links

### Option 3: Compress Media Files
- Compress videos to smaller formats (WebM, optimized MP4)
- Convert GIFs to WebP or compressed formats
- Use lower resolution versions for development

## Current Setup
The repository now contains all the code and smaller assets, making it easy to clone and work with. The large media files can be added separately if needed for production deployment. 