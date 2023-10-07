<!-- Inspiration: https://hub.meltano.com/utilities/tableau -->
# PowerBI

PowerBI is a meltano utility extension for PowerBI.

## Getting Start

### Installation

Add the following to your `meltano.yml` configuration file:
```yaml
plugins:
  utilities:
    - name: powerbi-ext
      namespace: powerbi-ext
      pip_url: -e .
      commands:
        help: --help
```

Then install your project
```
meltano install
```

### Configuration

Add the following environments variables:
```
POWERBI_EXT_TENANT_ID=...
POWERBI_EXT_CLIENT_ID=...
POWERBI_EXT_CLIENT_SECRET=...
```

or configurate using Meltano 
```
# Configure plugin interactively
meltano config powerbi-ext set --interactive
```
### Invoking

```
# run with node selection criteria
meltano invoke powerbi refresh -w <workspace_id> <dataset_id>

# run with a command specified in meltano.yml
meltano invoke powerbi:my_command
```

## Local development

1. Install the project dependencies with `poetry install`:

```shell
cd path/to/your/project
poetry install
```

2. Verify that you can invoke the extension:

```shell
poetry run powerbi --help
poetry run powerbi describe --format=yaml
```