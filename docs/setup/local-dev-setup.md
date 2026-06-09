# Local Development Setup

## Environment Status

Status: Partial

Node 22 and npm were installed with the existing local `nvm` installation and are usable when `nvm` is sourced. The default shell did not initially expose `node` or `npm` on `PATH`, so add the shell initialization snippet below if new terminals still cannot find them.

## macOS Setup

This repo standardizes Node 22 through `.nvmrc`.

If `nvm` is already installed:

```sh
source "$HOME/.nvm/nvm.sh"
nvm install 22
nvm use 22
node -v
npm -v
```

To load `nvm` automatically in zsh, add this to `~/.zshrc`:

```sh
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && . "$NVM_DIR/bash_completion"
```

If Homebrew is installed and you prefer Homebrew-managed Node:

```sh
brew install node@22
brew link --overwrite --force node@22
node -v
npm -v
```

If neither `nvm` nor Homebrew is installed:

```sh
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm install 22
nvm use 22
```

## Windows Setup

Recommended option with winget:

```powershell
winget install OpenJS.NodeJS.LTS
node -v
npm -v
```

Alternative option with nvm-windows:

```powershell
winget install CoreyButler.NVMforWindows
nvm install 22
nvm use 22
node -v
npm -v
```

After installing Node, run the repo verification commands from the repository root.

## Node/npm Setup

Use Node 22 for all Tollio AI JavaScript work:

```sh
cat .nvmrc
source "$HOME/.nvm/nvm.sh"
nvm use 22
npm install
npm run --if-present lint
npm run --if-present test
```

Current scripts:

- `lint`: not defined yet.
- `test`: foundation placeholder only; it reports that no tests are configured yet.

## Python Setup

Python is used for future FastAPI service work. Verify Python and pip:

```sh
python3 --version
pip3 --version
```

If Python 3 is missing on macOS, install it with one of these options:

```sh
xcode-select --install
```

or:

```sh
brew install python
```

If Python is missing on Windows:

```powershell
winget install Python.Python.3.12
python --version
pip --version
```

## Environment Verification Commands

Run these from the repository root:

```sh
git status --short --branch
node -v
npm -v
git --version
python3 --version
pip3 --version
cat .nvmrc
cat package.json
test -f .env.example
test -f docs/backlog/TOL-BACKLOG.md
npm install
npm run --if-present lint
npm run --if-present test
```

If `node` or `npm` are not found, source `nvm` first:

```sh
source "$HOME/.nvm/nvm.sh"
nvm use 22
```

## Troubleshooting

- `node: command not found`: source `~/.nvm/nvm.sh`, then run `nvm use 22`.
- `npm: command not found`: verify Node is active with `node -v`; npm ships with Node installed by `nvm`.
- `N/A: version "v22" is not yet installed`: run `nvm install 22`.
- `nvm: command not found`: install `nvm` or add the `NVM_DIR` snippet to your shell profile.
- `npm run --if-present lint` has no output: the repo does not define a lint script yet.
- `npm run --if-present test` reports no tests configured: this is expected for the foundation scaffold.
- Never place real secrets in `.env.example`; use placeholders only.
