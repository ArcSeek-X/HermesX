# Architecture atlas validation

2026-11-04 baseline: 13 architecture views, 180 nodes, 812 source records, 40 manifest pages.

2026-11-05 supplement: added view 14 (token-gateway). The atlas now has 14 views, 192 nodes, 815 source records and 40 manifest pages. Only the new view and the atlas data structure were re-validated; the other 13 views retain their 2026-11-04 records below.

All delivered views: showcase 9/9, zero errors and warnings. Browser evidence: passed at 1440x900, 1600x1000, 1920x1080, and 2048x1320. No viewport overflow. Theme loading timeout passed on retry.

Visual review: inspected frontend at 2048x1320 light and the other twelve views at 1440x900 dark. No visible clipping or label obstruction in inspected screenshots. Not every theme/viewport pair was manually inspected.

Atlas navigation, card counts, search, empty search, source expansion, fullscreen/Escape, 40-page inventory and horizontal containment at five widths passed browser checks. Final catalog updates were checked structurally. Exports were not individually exercised.

| View | Validation | Browser evidence | Artifact SHA-256 |
| --- | --- | --- | --- |
| system | 9/9 | passed | 13ac49ca774c47d3c5e2d6957f16b700c2d0f5b4de63784be95c286bbbf70d71 |
| frontend | 9/9 | passed | 8b627a77fecd92f8ad22b631be2c2548d6db368b8e95721c20e3f40fa7e16127 |
| backend | 9/9 | passed | c8c02fa2dbd40d197609cde3f5727c6adb4bca1fb4869e30fc098ddff32c9790 |
| routes | 9/9 | passed | c864f3e79176e0c286710de4dd4200fa68684f989fa7fc95943cf4b8d6a4d3d9 |
| pages | 9/9 | passed | 27b3879b29f69af52973900ec07814a4321c92f8937ee810f7c2eb6cb0059847 |
| theme | 9/9 | passed | a47bcc1deb7938a8049d042015928dca9ff01dd79b0c59787ae2a1f299a0a1a4 |
| analysis | 9/9 | passed | 72bde38527a228337465072b12eef651bfd417e73fe8a55cb2a7f769e603fbf5 |
| agent | 9/9 | passed | a49e142aa93225bd9646fa33febb91aa205c2c4b16b759d6c1ad2276fb8ed14d |
| quote | 9/9 | passed | c3b33b37ed32e38f49165f93261e39035965982c7fe9439ee2935e7acb3140b7 |
| persistence | 9/9 | passed | bf820cf0e9eb012fe06b66015ab368057878a6b8874be5f0d33eab9b1ae94abb |
| delivery | 9/9 | passed | cff2426ca7c6c56faaff1e2698e66dbb52895a8cae85cbc287f7e01648147d54 |
| control | 9/9 | passed | 1807979c5208bb24433f7c95b4e9d3391f22d04fb48fbe7c805400e70ec69d46 |
| desktop | 9/9 | passed | 8deee18b52a18ec87be8dfeb00cc6909a946dea98af696abf752a3af7091a066 |
| token-gateway (2026-11-05) | 9/9 | passed | c22b33b4d549379c0ec88705db8f47f7a9c2bc9fca0da2e1fb45affdc6ec9fd8 |

Specification SHA-256 and byte counts: see individual *.receipt.json. Temporary screenshots and full browser receipts: /tmp/hermesx-archify-V2-detailed-evidence/ (outside the repository).

Docs only, tests not run. Application workflows, online dependencies and desktop packages were not tested. Source inventory is static extraction plus targeted semantic review, not a line-by-line audit of all 815 files.

2026-11-05 token-gateway: showcase 9/9, zero errors and warnings; automated browser evidence passed at 1440x900, 1600x1000, 1920x1080 and 2048x1320 (light containment plus light/dark captures). Perceptual review inspected the delivered 1440x900 light and 2048x1320 dark screenshots: no visible clipping or label obstruction. Atlas navigation was checked structurally only (14 graphs, 12 new nodes, edge indices, source evidence and chapter ordering); the other 13 views were not re-opened in a browser. Temporary screenshots and browser receipts: /tmp/hermesx-archify-V2-token-gateway-evidence/ (outside the repository).
