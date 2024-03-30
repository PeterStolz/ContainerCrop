# ContainerCrop Action
<p align="center">
<a href="https://github.com/PeterStolz/ContainerCrop/actions/workflows/pytests.yaml/badge.svg"><img src="https://github.com/PeterStolz/ContainerCrop/actions/workflows/pytests.yaml"/>
</a>
<a href="https://codecov.io/gh/PeterStolz/ContainerCrop" >
 <img src="https://codecov.io/gh/PeterStolz/ContainerCrop/graph/badge.svg?token=32RZF4Y1Q2"/>
 </a>
 </p>

The `ContainerCrop` GitHub Action allows you to delete unwanted GitHub Container Registry (GHCR) images directly from your CI workflows. It offers a flexible way to manage your container images by specifying criteria such as cut-off date, and tag filtering.

## Inputs

- `image-name`: **Required** The name of the image you want to delete.
- `cut-off`: **Required** The cut-off date for deleting images older than this date. Must include a timezone, e.g., '2 days ago UTC'.
- `token`: **Required** A personal access token with read and delete scopes.
- `untagged-only`: Restrict deletions to images without tags. Default: `false`.
- `skip-tags`: Restrict deletions to images without specific tags. Supports Unix-shell style wildcards.
- `keep-at-least`: How many matching images to keep, regardless of other conditions. Default: `0`.
- `filter-tags`: Comma-separated list of tags to consider for deletion. Supports Unix-shell style wildcards.
- `dry-run`: If set to `true`, the action will not actually delete images. Instead, it will print out what would have been deleted. Default: `false`.

## Example Usage

Here is an example workflow that uses the `ContainerCrop` action to delete images:

```yaml
name: Clean Up Container Registry

on:
  schedule:
    - cron: '0 0 * * *'  # Runs every day at midnight

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
    - name: Delete Unwanted GHCR Images
      uses: peterstolz/containercrop@v1
      with:
        image-name: 'your-image-name'
        cut-off: '30 days ago UTC'
        token: ${{ secrets.GITHUB_TOKEN }}
        untagged-only: 'true'
        keep-at-least: '5'
        dry-run: 'false'
```

## Notes

- Ensure that the `token` provided has the necessary permissions to read and delete container images.
- The `cut-off` input is crucial for determining which images are considered "old" and eligible for deletion.
- Use the `dry-run` option to safely check what would be deleted before performing actual deletions.

For more detailed information, refer to the test cases in `containercrop/test_retention.py`

---

Remember to replace `your-github-username` with your actual GitHub username and adjust the `image-name` and other inputs as necessary for your specific use case.
