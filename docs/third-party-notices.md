# Third-party notices for the Windows desktop Alpha

The portable Windows build combines the Apache-2.0 licensed
`llm-interview-lab` code with redistributable third-party software. This file
is informational; the license files shipped by each dependency remain
authoritative.

## Qt for Python / PySide6

The desktop interface uses Qt for Python (PySide6) and Qt 6. The community
packages are available under the GNU Lesser General Public License version 3
and alternative licenses described by the Qt project. The portable archive
includes the corresponding runtime libraries without changing the
Apache-2.0 license of this project's own source code.

- Project: <https://doc.qt.io/qtforpython-6/>
- Licensing: <https://www.qt.io/licensing/open-source-lgpl-obligations>
- Source: <https://code.qt.io/cgit/pyside/pyside-setup.git/>

Recipients may replace or relink the covered libraries as allowed by their
licenses. For the exact versions in a release, inspect its build provenance
and dependency metadata.

## any-llm

Optional multi-provider chat support uses Mozilla's `any-llm-sdk`, licensed
under Apache-2.0.

- Project and source: <https://github.com/mozilla-ai/any-llm>

Provider-specific SDKs are loaded only when their adapter is selected. Their
own notices and terms continue to apply.

## Nuitka

The Windows executable is produced with Nuitka. Nuitka's build tooling and
runtime components retain their respective licenses and runtime exceptions.

- Project: <https://nuitka.net/>
- Source and license: <https://github.com/Nuitka/Nuitka>

## Python dependencies

The release workflow records the exact dependency versions used for each
artifact. To inspect locally:

```powershell
python -m pip list
python -m pip show PySide6 any-llm-sdk keyring Nuitka
```

No maintainer Profile, API key, Oracle submission, or private test is an
intended part of the portable artifact. The release check fails when those
known private paths appear in the build report.
