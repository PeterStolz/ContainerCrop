# ContainerCrop Action
<p align="center">
 <a href="https://www.python.org/downloads/release/python-3120/">
  <img src="https://img.shields.io/badge/python-3.12-blue.svg">
 </a>
 <a href="https://github.com/PeterStolz/ContainerCrop/actions/workflows/pytests.yaml">
  <img src="https://github.com/PeterStolz/ContainerCrop/actions/workflows/pytests.yaml/badge.svg"/>
 </a>
 <a href="https://codecov.io/gh/PeterStolz/ContainerCrop" >
  <img src="https://codecov.io/gh/PeterStolz/ContainerCrop/graph/badge.svg?token=32RZF4Y1Q2"/>
 </a>
 <a href="https://github.com/psf/black">
  <img src="https://img.shields.io/badge/code%20style-black-000000.svg">
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
    - name: Delete untagged images older than 30 days
      uses: peterstolz/containercrop@v1.0.2
      with:
        image-name: 'your-image-name'
        cut-off: '30 days ago UTC'
        token: ${{ secrets.GITHUB_TOKEN }}
        untagged-only: 'true'
        keep-at-least: '5'
        dry-run: 'true'
```

If you have multiple images you can use the matrix strategy to apply the same policies to them:
```yaml
jobs:
  delete-images:
    runs-on: ubuntu-latest
    strategy:
        matrix:
          image: [container1, container2, container3, container4]
    steps:
    - name: Delete old tagged images older than one week keeping 7
      uses: peterstolz/containercrop@v1.0.2
      with:
        image-name: my-repo-name/${{ matrix.image }}
        cut-off: 'a week ago UTC'
        token: ${{ secrets.YOUR_TOKEN }}
        filter-tags: "*.*.*"
        keep-at-least: '7'
        dry-run: 'true'

    - name: Delete all untagged images older than 2 days
      uses: peterstolz/containercrop@v1.0.2
      with:
        image-name: my-repo-name/${{ matrix.image }}
        cut-off: 'two days ago UTC'
        token: ${{ secrets.YOUR_TOKEN }}
        untagged-only: 'true'
        dry-run: 'true'

```

## Notes

- Ensure that the `token` provided has the necessary permissions to read and delete container images.
- The `cut-off` input is crucial for determining which images are considered "old" and eligible for deletion.
- Use the `dry-run` option to safely check what would be deleted before performing actual deletions.

For more detailed information, refer to the test cases in `./containercrop/test_retention.py`
