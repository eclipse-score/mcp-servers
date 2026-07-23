<!--
*******************************************************************************
Copyright (c) 2026 Contributors to the Eclipse Foundation

See the NOTICE file(s) distributed with this work for additional
information regarding copyright ownership.

This program and the accompanying materials are made available under the
terms of the Apache License Version 2.0 which is available at
https://www.apache.org/licenses/LICENSE-2.0

SPDX-License-Identifier: Apache-2.0
*******************************************************************************
-->

# Eclipse S-CORE Agent Context Attention Layer

This repository contributes infrastructure for the
[Eclipse Safe Open Vehicle Core](https://projects.eclipse.org/projects/automotive.score)
(S-CORE) project. The source code is hosted on
[GitHub](https://github.com/eclipse-score).

Please note that the Eclipse Foundation's
[Terms of Use](https://www.eclipse.org/legal/terms-of-use/) apply. Contributors
must sign the [Eclipse Contributor Agreement (ECA)](https://www.eclipse.org/legal/ECA.php)
and follow the [Developer Certificate of Origin (DCO)](https://www.eclipse.org/legal/dco/).
Every commit must include a `Signed-off-by` trailer.

## Contributing

### Getting the source code and building

Refer to [README.md](README.md) for the repository overview. The Python
workspace uses [uv](https://docs.astral.sh/uv/):

```shell
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```

### Getting involved

Please use GitHub issues and pull requests for contributions. Keep pull
requests focused, describe the motivation and verification performed, and mark
them as drafts until they are ready for committer review. Reviews and final
merges are performed according to the
[Eclipse Foundation Project Handbook](https://www.eclipse.org/projects/handbook/).

For a contribution:

1. Open or identify an issue describing the bug, improvement, or governance
   change.
2. Create a focused branch and pull request.
3. Run the checks documented in the README and report the results.
4. Ensure every commit has the required DCO sign-off.

All contributions are subject to the Eclipse Foundation project processes and
the applicable community code of conduct.
