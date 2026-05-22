# CHANGELOG

<!-- version list -->

## v0.2.1 (2026-05-22)

### Bug Fixes

- **packaging**: Wire package READMEs so PyPI pages render
  ([`d82320b`](https://github.com/godoo-dev/godoo-py/commit/d82320b249312828da237d7a789bfdb9eb6c2384))

### Documentation

- **04**: Phase verification passed — RELEASE-01/02/03 satisfied
  ([`4a4b8a0`](https://github.com/godoo-dev/godoo-py/commit/4a4b8a00749b6656bee29e7e06c1603029b38a58))

- **04-03**: Complete publish plan — SUMMARY, ROADMAP, STATE
  ([`393a3de`](https://github.com/godoo-dev/godoo-py/commit/393a3de246fc91a40f7a15ec6b489c49b06fb871))

- **04.1**: Add code review report
  ([`9303230`](https://github.com/godoo-dev/godoo-py/commit/9303230f82557a335c042b7aa28f0eea30549972))

- **04.1**: Add phase research — verified symbols, URLs, pre-alpha landmine
  ([`641300f`](https://github.com/godoo-dev/godoo-py/commit/641300fb241bb6fdad486b0a4bc03147dd72cf4a))

- **04.1**: Capture phase context
  ([`1cb9c9b`](https://github.com/godoo-dev/godoo-py/commit/1cb9c9befc4961c3e4f833c0195013686d4ad878))

- **04.1**: Create phase plan — wire readme keys + author three package READMEs
  ([`44aba40`](https://github.com/godoo-dev/godoo-py/commit/44aba4003a2ac7991a3cf5f1dcb759fea7cbe569))

- **04.1-01**: Complete plan — wire package READMEs execution summary
  ([`9e64054`](https://github.com/godoo-dev/godoo-py/commit/9e64054c6342c0093f4424a86ce0a1b3ced0415f))

- **phase-04.1**: Complete phase execution
  ([`fb553e9`](https://github.com/godoo-dev/godoo-py/commit/fb553e9dd9ff696955caa5f0994cb50269b9be4c))

- **phase-04.1**: Evolve PROJECT.md after phase completion
  ([`52ba19f`](https://github.com/godoo-dev/godoo-py/commit/52ba19fe031132c929f41747efcfec61ad15d24d))

- **state**: Record phase 04.1 context session
  ([`c40ae6b`](https://github.com/godoo-dev/godoo-py/commit/c40ae6ba225794856f8f32e2d713b77ce12f1a66))


## v0.2.0 (2026-05-22)

### Bug Fixes

- **01**: Revise plans based on checker feedback (5 blockers, 3 warnings)
  ([`092015e`](https://github.com/godoo-dev/godoo-py/commit/092015e467130e1fed78891bfc487472fac2acce))

- **01-01**: Add configurable timeout to transport and fix TimeoutException handling
  ([`53868e7`](https://github.com/godoo-dev/godoo-py/commit/53868e700f72ca4c1df1b0cbf1f7c36bf721c426))

- **01-02**: Remove async from CdcService.get_feed so it returns async generator directly (FIXES-01)
  ([`ed9a9ba`](https://github.com/godoo-dev/godoo-py/commit/ed9a9baa6430362de72de4c9bd191dfccfc46155))

- **01-05**: Guard read_binary base64 decode; raise OdooValidationError on malformed input (CR-02)
  ([`26eeea6`](https://github.com/godoo-dev/godoo-py/commit/26eeea651c46abaf008d3a1f3b76f76e9f63f21c))

- **01-05**: Preserve body exception in __aexit__ when aclose() fails (WR-04)
  ([`e098a72`](https://github.com/godoo-dev/godoo-py/commit/e098a72606f938211b83746913194e38e13588f8))

- **02**: Drop packages/godoo-introspection/tests/__init__.py — collides with
  godoo/tests/__init__.py during monorepo pytest collection
  ([`b5351d5`](https://github.com/godoo-dev/godoo-py/commit/b5351d526bcd56898cb093650fa874dcb7a445e6))

- **03**: CR-01/CR-02/WR-01/WR-02/WR-04 + WR-03 doc in OdooTestContainer.start/cleanup
  ([`5d63d9d`](https://github.com/godoo-dev/godoo-py/commit/5d63d9d3619ad3dc0b58925ac7fada618a7c1c22))

- **03**: CR-01/WR-05 honour snapshot-disable in save path and canonicalise snapshot dir
  ([`e6cb3f5`](https://github.com/godoo-dev/godoo-py/commit/e6cb3f53a4740a684970724a7f0756fcea5aa266))

- **04**: Add explicit_package_bases + mypy_path for namespace packages (D-08)
  ([`459bf1e`](https://github.com/godoo-dev/godoo-py/commit/459bf1ed8ebaf634af4b2abb9ddda5c6b6f07abc))

- **04**: Revise plans based on checker feedback
  ([`9a43f12`](https://github.com/godoo-dev/godoo-py/commit/9a43f12da7314893660faa8ff1ef01880f7e85cb))

- **04**: Ruff format 4 testcontainers files (pre-existing formatting drift)
  ([`f3e9642`](https://github.com/godoo-dev/godoo-py/commit/f3e96420eb9eb356fe1e7c293b0557b6f15f6e21))

- **release**: Fix semantic-release config and revert versions to 0.1.0
  ([`844f265`](https://github.com/godoo-dev/godoo-py/commit/844f265f4f7b252a50c02151bcdca88fc41977d6))

- **release**: Revert all packages to 0.1.0 and replace v1.0.0 tag with v0.1.0
  ([`e78d383`](https://github.com/godoo-dev/godoo-py/commit/e78d3836025bed5289b8e4a021941ec26830a464))

### Chores

- Add GitHub Sponsors funding
  ([`2f9d756`](https://github.com/godoo-dev/godoo-py/commit/2f9d7561fa547bef731a439aea942849218d06a1))

- Add project config
  ([`cc903d3`](https://github.com/godoo-dev/godoo-py/commit/cc903d3320ab0cc81dfb94a740bbbb379a7d8df0))

- Add project config
  ([`24cf45c`](https://github.com/godoo-dev/godoo-py/commit/24cf45c92bb5ad8492d1c86125a65de3dcdb7809))

- Supersede prior planning artifacts
  ([`a691f13`](https://github.com/godoo-dev/godoo-py/commit/a691f130c0582ac81af0cd911f09fb8b4acf8f6f))

- Sync uv.lock with package versions (0.1.0 -> 0.1.1)
  ([`a5736a4`](https://github.com/godoo-dev/godoo-py/commit/a5736a4bd7e3fee1fe8b0eb3e13ad87c224a57bb))

- Sync uv.lock with package versions (0.1.0 -> 0.1.1)
  ([`733d34a`](https://github.com/godoo-dev/godoo-py/commit/733d34acc17ac4e5cb447f02ab1fe39232013d74))

- **01**: Drop mis-classified HUMAN-UAT
  ([`6020324`](https://github.com/godoo-dev/godoo-py/commit/602032442e6ce8b2876e8350a6f9345686f4b036))

- **01-02**: Sync uv.lock with package versions (0.1.0 -> 0.1.1)
  ([`f2b7f02`](https://github.com/godoo-dev/godoo-py/commit/f2b7f0233ec3302d22357a4f152d4b3052ce9906))

- **02-01**: Drop INTRO-05 from planning docs and add py.typed marker
  ([`2ea4391`](https://github.com/godoo-dev/godoo-py/commit/2ea4391ef27da282f51caece5071c8ff43f05699))

- **03-01**: Add py.typed PEP 561 marker for godoo-testcontainers
  ([`bb07968`](https://github.com/godoo-dev/godoo-py/commit/bb07968110968a99636e8406a47f4b85c97f1bbf))

- **04**: Update pyproject.toml files for namespace packaging and rename godoo->godoo-client
  ([`714e352`](https://github.com/godoo-dev/godoo-py/commit/714e35292e41390fa66e49c5f0ea53e2232596b8))

- **04**: Wire four distributions into semantic-release build (D-04, D-05)
  ([`e959c55`](https://github.com/godoo-dev/godoo-py/commit/e959c555d90ef267b8711931fd692426cc2b84dd))

### Code Style

- **01-05**: Apply ruff format to client.py and test_client.py
  ([`4db73fb`](https://github.com/godoo-dev/godoo-py/commit/4db73fb347c4bee6b445d694555dd5514bd649a7))

- **04**: Fix import ordering after namespace restructure (ruff I001)
  ([`697e825`](https://github.com/godoo-dev/godoo-py/commit/697e825dbecabb0948b14852bf8480782dc8e60c))

### Continuous Integration

- Release triggers after test completes (workflow_run), not inline
  ([`88bd7cd`](https://github.com/godoo-dev/godoo-py/commit/88bd7cdc3725682c097addfb5291bd010f9fa55b))

- Test pipeline, docs deployment, release automation, docker seed infra
  ([`4bde802`](https://github.com/godoo-dev/godoo-py/commit/4bde802f725d463e417a2fc7a39a78b850e025f1))

- **04**: Make uv publish idempotent with --check-url
  ([`4c54a4b`](https://github.com/godoo-dev/godoo-py/commit/4c54a4b6195cfece9a5917029418eae8aed29ea4))

- **release**: Re-enable PyPI publishing
  ([`c47420a`](https://github.com/godoo-dev/godoo-py/commit/c47420abf57711e6354273a9d39675dda8b1f8f8))

- **release**: Re-enable PyPI publishing
  ([`badbdc9`](https://github.com/godoo-dev/godoo-py/commit/badbdc9dd2373c6ac46431f9fae38048f53113fb))

### Documentation

- Add research summary
  ([`2254fe2`](https://github.com/godoo-dev/godoo-py/commit/2254fe2aad8b89c0c473926f9a4304e92291f972))

- Complete project research
  ([`6a2591f`](https://github.com/godoo-dev/godoo-py/commit/6a2591f6d2039b8810955a351a3d9d81d428d681))

- Create roadmap (4 phases)
  ([`ca3bc5c`](https://github.com/godoo-dev/godoo-py/commit/ca3bc5cbe522be7be47867622fe1d96e9c99eba6))

- Create v1 roadmap and state
  ([`93b0271`](https://github.com/godoo-dev/godoo-py/commit/93b0271de05fcdbb3c49a6d81dde6d7e627f70cf))

- Define v1 requirements
  ([`7e1c152`](https://github.com/godoo-dev/godoo-py/commit/7e1c152401418f637c0747a9af3c47df6d0c6047))

- Define v1 requirements
  ([`e47d1cc`](https://github.com/godoo-dev/godoo-py/commit/e47d1cc490b505982e9f3eafa14740bb47c426d3))

- Drop CLIENT-09 (OAuthProxyClient) from v1 scope
  ([`750f821`](https://github.com/godoo-dev/godoo-py/commit/750f8210089d73cf7a4adefdb5409b23e9963a7b))

- Initialize project
  ([`4e504f4`](https://github.com/godoo-dev/godoo-py/commit/4e504f46261063c6343dd39f2dca0e38989a7e1a))

- Initialize project
  ([`fdc08ba`](https://github.com/godoo-dev/godoo-py/commit/fdc08ba3b69aa6b270f5b4f015398430c344a41d))

- Map existing codebase
  ([`24b1ea9`](https://github.com/godoo-dev/godoo-py/commit/24b1ea91039763625e22d143294cff07d4233b13))

- Map existing codebase
  ([`6e236ea`](https://github.com/godoo-dev/godoo-py/commit/6e236eaba2b63c0623354d14d1fde7526e7b3184))

- Plant seed — browser/Pyodide compatibility (SEED-001)
  ([`98c741c`](https://github.com/godoo-dev/godoo-py/commit/98c741c4a2e2a2b10cb8db4af85e23154e390ace))

- README, CONTRIBUTING, CLAUDE.md, mkdocs-material site
  ([`ab74b03`](https://github.com/godoo-dev/godoo-py/commit/ab74b03b141df862ea051247e2e737934cfa5f60))

- **01**: Add code review report
  ([`07f38ab`](https://github.com/godoo-dev/godoo-py/commit/07f38ab48432b95f420a48d1ed093f8801552724))

- **01**: Add gap-closure plan 01-05 (CR-02 + WR-03/04/05)
  ([`b56b1fc`](https://github.com/godoo-dev/godoo-py/commit/b56b1fc6f41745bb79ee5902c4b0b8ceba112761))

- **01**: Capture phase context
  ([`3e6886c`](https://github.com/godoo-dev/godoo-py/commit/3e6886ca713f70fb0597c7c36fac55ad33a6be14))

- **01**: Create phase 1 plan — 4 plans across 3 waves
  ([`72a9955`](https://github.com/godoo-dev/godoo-py/commit/72a9955e4966c5588d0880f6b1296dfb0b1d54f2))

- **01**: Create phase plan
  ([`3f5b173`](https://github.com/godoo-dev/godoo-py/commit/3f5b1737367b5dbd8a7e132cb7c419da4088c80c))

- **01**: Research phase — client parity
  ([`7269d19`](https://github.com/godoo-dev/godoo-py/commit/7269d19cfd8d5d7fdbe680fe965f04edbd6dfca4))

- **01-01**: Complete transport timeout fixes plan summary
  ([`e0908ac`](https://github.com/godoo-dev/godoo-py/commit/e0908ac5d279c7254e463a0f87e700c6ebbb1cd2))

- **01-02**: Complete CdcService get_feed fix and py.typed marker plan
  ([`3ad62e8`](https://github.com/godoo-dev/godoo-py/commit/3ad62e837195ea6a740e1fda484541fc0abcdef6))

- **01-03**: Complete CLIENT-01/02/03 plan — async ctx manager, with_context, iter_search_read
  ([`084f1e0`](https://github.com/godoo-dev/godoo-py/commit/084f1e085d64b90e98c3dd895e04d0aba3e8f2c0))

- **01-04**: Complete client-parity plan 04 summary
  ([`0cf3863`](https://github.com/godoo-dev/godoo-py/commit/0cf386332ad16cf292affe23d1d5d3ab18e08115))

- **01-05**: Complete gap-closure plan 01-05 (CR-02/WR-03/WR-04/WR-05)
  ([`342d08b`](https://github.com/godoo-dev/godoo-py/commit/342d08bc43b1b04c4a677adb6a7735a0cf8dd897))

- **01-05**: Correct with_context / _OdooContextScope docstrings for ContextVar semantics (WR-05)
  ([`4bc0750`](https://github.com/godoo-dev/godoo-py/commit/4bc0750f77d77f2b6741083f53921f5b1672451c))

- **02**: Apply checker revision — resolve open questions, fix element names, move codegen helper
  ([`36cc9db`](https://github.com/godoo-dev/godoo-py/commit/36cc9db682fd31af9c4a3ddc0856456a3700126c))

- **02**: Capture phase context
  ([`e946594`](https://github.com/godoo-dev/godoo-py/commit/e946594f88b0031c79112e7a50c3ec063c0fac56))

- **02**: Create phase 2 introspection plan — 2 plans, 2 waves
  ([`430d450`](https://github.com/godoo-dev/godoo-py/commit/430d450bedf72ce4f1f73bdfe3d24d328c576ad1))

- **02**: Create phase plan
  ([`4437fe4`](https://github.com/godoo-dev/godoo-py/commit/4437fe4a054d47a21c58c0515b8b890e0091c7c3))

- **02**: Mark phase 2 complete in state
  ([`f075cf3`](https://github.com/godoo-dev/godoo-py/commit/f075cf34b9cbaea45b282b9f667398b472c424bd))

- **02**: Record phase 2 verification — status passed (5/5 must-haves, 233/233 tests)
  ([`c3f481c`](https://github.com/godoo-dev/godoo-py/commit/c3f481c7eb1db06005e8c2cd5f31880d728f9250))

- **02**: Research phase introspection domain
  ([`83a2fdc`](https://github.com/godoo-dev/godoo-py/commit/83a2fdc07d21350b3d7df9a44c1e2ad6320d44c9))

- **02**: Update tracking after wave 2
  ([`383974a`](https://github.com/godoo-dev/godoo-py/commit/383974a212149dd76c2ab78898e7bd0836ae7fc1))

- **02-01**: Complete schema fetch + cache plan — SUMMARY.md
  ([`0e10130`](https://github.com/godoo-dev/godoo-py/commit/0e10130a6e023e60ba0441328fdfe29feae6c031))

- **02-02**: Complete type mapper + codegen plan — SUMMARY.md
  ([`599c7a7`](https://github.com/godoo-dev/godoo-py/commit/599c7a76072b9629e894d628ea9811e769ee67df))

- **03**: Add code review report
  ([`4b8261b`](https://github.com/godoo-dev/godoo-py/commit/4b8261b9c30b01413e55c443fc12771c0e5220ee))

- **03**: Add code review report
  ([`d8d01b9`](https://github.com/godoo-dev/godoo-py/commit/d8d01b9d5424d7afe43676ab3de610af2f0e18fe))

- **03**: Capture phase 3 context
  ([`93382d0`](https://github.com/godoo-dev/godoo-py/commit/93382d0003077d2689d2e899a4cb3f387622f91a))

- **03**: Create phase 3 plan — testcontainers parity (3 plans, 3 waves)
  ([`1bc4bcb`](https://github.com/godoo-dev/godoo-py/commit/1bc4bcb070f284a8fd753a184ac1d20eabb8c81a))

- **03**: Create phase plan
  ([`a631c82`](https://github.com/godoo-dev/godoo-py/commit/a631c821be463c8765e7e619ddfb2363e9e909f3))

- **03**: Research phase — snapshot mechanics, addons mount, properties provisioner
  ([`51ba8da`](https://github.com/godoo-dev/godoo-py/commit/51ba8dae5bad81f35487365f4e506202f77f74c7))

- **03-01**: Apply D-Drop-1 / D-Snap-3-amendment charter edits
  ([`fb9ce05`](https://github.com/godoo-dev/godoo-py/commit/fb9ce05b815d5c86e89fdf445d2927dcc631749d))

- **03-01**: Complete plan 1 — SUMMARY, STATE, ROADMAP, REQUIREMENTS updated
  ([`5771d7b`](https://github.com/godoo-dev/godoo-py/commit/5771d7b0833a8ca5e11eaf1d905e0e9b4f265dfb))

- **03-02**: Complete snapshot cache + addons mount plan — SUMMARY, STATE, ROADMAP, REQUIREMENTS
  updated
  ([`a43903c`](https://github.com/godoo-dev/godoo-py/commit/a43903cd7f4258a6a8c2670b71664a99dd550deb))

- **03-03**: Complete properties provisioner + TestHarness plan — phase 3 done
  ([`0d87bf8`](https://github.com/godoo-dev/godoo-py/commit/0d87bf895200a50ef63d988e7c3372a1ad39285f))

- **04**: Capture phase context
  ([`deaa00e`](https://github.com/godoo-dev/godoo-py/commit/deaa00e755904fe12db06ca46c7da5174e298c89))

- **04**: Create phase 4 release plan — 3 plans across 3 waves
  ([`eed95cf`](https://github.com/godoo-dev/godoo-py/commit/eed95cf772b1262c1b33d28ae8742f317394488b))

- **04**: Create phase plan
  ([`e5bb108`](https://github.com/godoo-dev/godoo-py/commit/e5bb108cc10358f7fa18651742077d431fff82e8))

- **04-01**: Complete github-ci plan — SUMMARY, STATE, ROADMAP, REQUIREMENTS updated
  ([`8354519`](https://github.com/godoo-dev/godoo-py/commit/8354519cacc543e7a5cfbe47ea6948848496a981))

- **04-02**: Complete namespace-restructure plan
  ([`e470531`](https://github.com/godoo-dev/godoo-py/commit/e470531c1db5a9a250038ef0fad69cbd291e5852))

- **phase-01**: Complete phase execution
  ([`255da17`](https://github.com/godoo-dev/godoo-py/commit/255da17751b627adbb679a255c9c29700898281c))

- **phase-01**: Evolve PROJECT.md after phase completion
  ([`969fa6e`](https://github.com/godoo-dev/godoo-py/commit/969fa6efb8849353f7a1da5646b41daf175e1ee0))

- **phase-01**: Update tracking after wave 1
  ([`9cbd66d`](https://github.com/godoo-dev/godoo-py/commit/9cbd66d8bfa84dff0572b47e10771d8c0b75e803))

- **phase-01**: Update tracking after wave 2
  ([`ce7fcfc`](https://github.com/godoo-dev/godoo-py/commit/ce7fcfc499abbfffd3c5b4877cc7a7701cdc46ea))

- **phase-01**: Update tracking after wave 3
  ([`4879fe0`](https://github.com/godoo-dev/godoo-py/commit/4879fe0a807f5028e481e1ff814fe9c4d84b4c3f))

- **phase-03**: Complete phase execution — verification passed via automated integration tests
  ([`bc61587`](https://github.com/godoo-dev/godoo-py/commit/bc615879895e159d8d8ffc13a06986873e6cdbeb))

- **state**: Record phase 1 context session
  ([`34c5d0d`](https://github.com/godoo-dev/godoo-py/commit/34c5d0df9b100ea94b766083f4bc647d7a704b9f))

- **state**: Record phase 2 context session
  ([`c67efdd`](https://github.com/godoo-dev/godoo-py/commit/c67efdd7eedcb564a879d06dc86193644a8c1e4b))

- **state**: Record phase 3 context session
  ([`44a2fc8`](https://github.com/godoo-dev/godoo-py/commit/44a2fc88f54c0285147c7be416cba90272e0fad7))

- **state**: Record phase 4 context session
  ([`56498b2`](https://github.com/godoo-dev/godoo-py/commit/56498b29a8820a78b9cfc5ccfa996692af6eb3ac))

### Features

- **01-02**: Add py.typed PEP 561 marker to godoo package (CLIENT-10)
  ([`0b03c66`](https://github.com/godoo-dev/godoo-py/commit/0b03c6641998cddb9dcfd6d2c286226b9aa033ef))

- **01-03**: Add __aenter__/__aexit__ and with_context to OdooClient
  ([`8bab5c5`](https://github.com/godoo-dev/godoo-py/commit/8bab5c5af11e29b594e51971383957990fefc432))

- **01-03**: Add iter_search_read keyset-paginated async generator
  ([`ee1c3cc`](https://github.com/godoo-dev/godoo-py/commit/ee1c3cc66b7627f0b3df719fecc94d02e0c6f87c))

- **01-04**: Implement fields_get, ref, execute_kw, read_binary, overloaded create
  ([`406e20c`](https://github.com/godoo-dev/godoo-py/commit/406e20ccd1c69513dc857d0c20e6d7801201656e))

- **02-01**: Complete __init__.py barrel and finalize test_introspector.py
  ([`8c666b8`](https://github.com/godoo-dev/godoo-py/commit/8c666b8a130e1712188a7f2a774854bc1cb24ed1))

- **02-01**: Implement markers.py, types.py, and introspector.py — schema fetch + cache
  ([`8ca855f`](https://github.com/godoo-dev/godoo-py/commit/8ca855fcbc9274f66c6568a0f593013d765513d1))

- **02-02**: Implement codegen.py — CodeGenerator with generate() and write() methods
  ([`8d28560`](https://github.com/godoo-dev/godoo-py/commit/8d2856020a4a36b2bdc56273a2cfec8d31c0e4e1))

- **02-02**: Implement type_mapper.py — python_type_str() for all D-Mapping-1 ttypes
  ([`da4fe85`](https://github.com/godoo-dev/godoo-py/commit/da4fe85c94a4fb24ae1e4b85467fe787add940a8))

- **03-02**: Implement snapshot.py — SnapshotConfig, key computation, save/restore
  ([`26014b1`](https://github.com/godoo-dev/godoo-py/commit/26014b1fc4289b56dd9f692e85f05c4b117e9201))

- **03-02**: Wire snapshot cache + addons mount into OdooTestContainer.start()
  ([`5af5d30`](https://github.com/godoo-dev/godoo-py/commit/5af5d3075be37a5c5cb23c409762e0784d89dee0))

- **03-03**: Implement ConfigParameterHelper and wire properties key into snapshot
  ([`60a5f70`](https://github.com/godoo-dev/godoo-py/commit/60a5f70ffddee31f6b2eb2d5e08c1d850371436c))

- **03-03**: Implement TestHarness async-cm and update package barrel exports
  ([`48090d0`](https://github.com/godoo-dev/godoo-py/commit/48090d09d5c9f02bebf66b866466bd16057edd12))

- **04**: Add godoo placeholder distribution (D-04)
  ([`18ae7af`](https://github.com/godoo-dev/godoo-py/commit/18ae7af944d1b079fd001c5253ead60d5a5d89f6))

### Refactoring

- **01-05**: Replace _safety_context Any with typed _UndefinedType sentinel (WR-03)
  ([`00fbf55`](https://github.com/godoo-dev/godoo-py/commit/00fbf555159c8125052f96c82e17a8ddb0a6b56b))

- **04**: Restructure all 3 packages into shared godoo PEP 420 namespace
  ([`30ca319`](https://github.com/godoo-dev/godoo-py/commit/30ca319cebeb769f5bd57a4f049f04ade59d037b))

### Testing

- **01**: Persist human verification items as UAT
  ([`2bb1bff`](https://github.com/godoo-dev/godoo-py/commit/2bb1bffe59fa1c4c65e3a4a911f2f7fb2e09c5e3))

- **01-01**: Add timeout tests for FIXES-02 and FIXES-03
  ([`5fc4c66`](https://github.com/godoo-dev/godoo-py/commit/5fc4c6639f41067f4c64dc06d2a0f9a2004004c0))

- **01-02**: Add failing test for CdcService.get_feed plain-def requirement
  ([`022eebc`](https://github.com/godoo-dev/godoo-py/commit/022eebccd71c5668ad951b766aab028b44cbd9ea))

- **01-03**: Add tests for CLIENT-01, CLIENT-02, CLIENT-03
  ([`21a89bf`](https://github.com/godoo-dev/godoo-py/commit/21a89bf14fe6de213d6c901bbc6ffd467a383d9d))

- **01-04**: Add failing tests for CLIENT-04/05/06/07/08
  ([`612e6d5`](https://github.com/godoo-dev/godoo-py/commit/612e6d56a949742dee4e822cd9019fd14d73f234))

- **01-05**: Add failing test for __aexit__ exception-preservation (WR-04 RED)
  ([`350b09f`](https://github.com/godoo-dev/godoo-py/commit/350b09f7e84a48ca0773712f21f2ad0281027e02))

- **02-01**: Add failing tests for Introspector, IntrospectionCache, FieldMeta, ModelSchema
  ([`e64359a`](https://github.com/godoo-dev/godoo-py/commit/e64359adadd6e56b07dcb5b404bc50c239cce01d))

- **02-02**: Add failing tests for CodeGenerator — 14 cases covering generate/write/helpers
  ([`8f6ac12`](https://github.com/godoo-dev/godoo-py/commit/8f6ac120b6d95be0bc21d3be73f0eec4994b51e5))

- **02-02**: Add failing tests for python_type_str — 22 cases covering all D-Mapping-1 ttypes
  ([`0f4d417`](https://github.com/godoo-dev/godoo-py/commit/0f4d4178299410321042474cb809f8d7259540fc))

- **03**: Add Docker integration tests for snapshot, addons mount, and TestHarness
  (TESTC-01/02/06/07)
  ([`a4c93d1`](https://github.com/godoo-dev/godoo-py/commit/a4c93d19eef709802e7f1f572054d705c6e3c6d2))

- **03**: Persist human verification items as UAT
  ([`4b54b83`](https://github.com/godoo-dev/godoo-py/commit/4b54b83f8239717fdca2a5cc8236dcf84bf43871))

- **03-02**: Add snapshot unit tests and extend container param tests
  ([`1b2c383`](https://github.com/godoo-dev/godoo-py/commit/1b2c3833272e79ddb9c0ad33781af61822e304c2))

- **03-03**: Add unit tests for ConfigParameterHelper and TestHarness lifecycle
  ([`225ce5e`](https://github.com/godoo-dev/godoo-py/commit/225ce5e161aed15c912f2374a0cbcbec0e8f0d12))


## v0.1.1 (2026-03-26)

### Bug Fixes

- **release**: Fix semantic-release config and revert versions to 0.1.0
  ([`844f265`](https://github.com/marcfargas/godoo/commit/844f265f4f7b252a50c02151bcdca88fc41977d6))

- **release**: Revert all packages to 0.1.0 and replace v1.0.0 tag with v0.1.0
  ([`e78d383`](https://github.com/marcfargas/godoo/commit/e78d3836025bed5289b8e4a021941ec26830a464))

### Chores

- Add GitHub Sponsors funding
  ([`2f9d756`](https://github.com/marcfargas/godoo/commit/2f9d7561fa547bef731a439aea942849218d06a1))

### Continuous Integration

- Release triggers after test completes (workflow_run), not inline
  ([`88bd7cd`](https://github.com/marcfargas/godoo/commit/88bd7cdc3725682c097addfb5291bd010f9fa55b))

- Test pipeline, docs deployment, release automation, docker seed infra
  ([`4bde802`](https://github.com/marcfargas/godoo/commit/4bde802f725d463e417a2fc7a39a78b850e025f1))

### Documentation

- README, CONTRIBUTING, CLAUDE.md, mkdocs-material site
  ([`ab74b03`](https://github.com/marcfargas/godoo/commit/ab74b03b141df862ea051247e2e737934cfa5f60))


## v0.1.0 (2026-03-24)

- Initial Release
