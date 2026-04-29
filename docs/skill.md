# PagePop Skill

`packages/pagepop-skill` contains the generic installable PagePop skill.

The skill should remain host-neutral. Host-specific guidance belongs under `adapters/<host>`.

## Build-Time Fields

The build script renders `skill-manifest.json` from `skill-manifest.template.json`.

Required fields:

- `PAGEPOP_SKILL_ID`
- `PAGEPOP_PACKAGE_VERSION`
- `PAGEPOP_SKILL_CHANNEL`
- `PAGEPOP_RELEASE_REPO`
- `PAGEPOP_RELEASE_TAG`

Generated fields:

- `PAGEPOP_BUILD_SHA`
- `PAGEPOP_PUBLISHED_AT`

## Production Defaults

Production builds use:

- `PAGEPOP_SKILL_CHANNEL=prod`

Non-production builds require `--allow-non-prod` and must not be published as public GitHub Releases.
