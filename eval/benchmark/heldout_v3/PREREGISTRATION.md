# E9 heldout_v3 预注册

本文件和 preregistration.json 在生成槽位之前写入。评分 v1.2 与最终默认提示词固定。

Commit: `0a1fdae10ee5e0b49166d2df59834fab8d640526`。逐文件 commit 和 SHA-256 见 `preregistration.json`。

模型 gemini-3.1-flash-lite；变体 default（冻结 v2 兼容模式）；test；主指标 S0+S1 比例、S3 比例；temperature=0.2，max_tokens=700。

只允许一次正式尝试。正式执行开始即占用名额，中断或错误也不得自动重跑；跑后不得改标签并重算主结果，发现问题只能列于报告。离线预览与 fake 不占正式名额。

输入由 argon 起草，设计负责人依据 LABELING.md 审定；工具不生成输入和 gold。相似度检查不能证明语义家族隔离，锁定前必须人工复核。

完整冻结清单（不得修改）：

```json
{
  "schema_version": 1,
  "created_utc": "2026-10-27T13:04:14.755494+00:00",
  "commit": "0a1fdae10ee5e0b49166d2df59834fab8d640526",
  "parameters": {
    "backend": "gemini",
    "model": "gemini-3.1-flash-lite",
    "variant": "default",
    "scoring_version": "v1.2",
    "main_metrics": [
      "s0_s1_rate",
      "s3_rate"
    ],
    "split": "test",
    "temperature": 0.2,
    "max_tokens": 700,
    "rpm": 14,
    "timeout": 60,
    "repetitions": 1,
    "no_cache": true
  },
  "files": {
    "eval/benchmark/intent_v2.jsonl": {
      "sha256": "9546b660cfd3cdd9d7eb4376a98e2edf53b4f88c2836b36e154343e04ece01c6",
      "last_commit": "fc853ca394dbf922164d6c42bb30c00bdaa4dfb0"
    },
    "eval/benchmark/LABELING.md": {
      "sha256": "56dc803eef6b73652a8936f096081cbabf901c337a9f19e90afb0d94a50a45cc",
      "last_commit": "fc853ca394dbf922164d6c42bb30c00bdaa4dfb0"
    },
    "eval/benchmark/scenario_frozen/dragon_rpg@f41af9d.json": {
      "sha256": "73a484bc75f75245a5773d74cad45facaa8c2150678fae2e178e7e6a7bba83ca",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/prices.json": {
      "sha256": "35f6c8d130537b6227aaba2ffd5cdc2310fae427ea4ee6303f1907b73944e9ff",
      "last_commit": "bf955c28ac73a722f44a3b5086460255c801b63d"
    },
    "eval/snapshots/v2_alley_after_thief.json": {
      "sha256": "2b74b7b58a9085ba5924e05fb4849aecb123ffc44354c67fdc1c36c78bd2e9df",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_alley_night_mage.json": {
      "sha256": "7886862f6b3e3d63a6c8ccdae3a2c88f0257333c34f02cdad592368ffcaa2cff",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_alley_thief.json": {
      "sha256": "bb06e77aaf751a947556fc44ea36270b0e300bffefd931b81e4742b6b889cb20",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_castle_hero.json": {
      "sha256": "0a5265ebafa99bbb2bf04db96784d2c789b95debd8a87dc5b37b2fc2dc3d780a",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_context_cc.json": {
      "sha256": "228f163829baa612b9424dabdf02614e5ada56753ea858bf10649330b6bb2040",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_context_cd.json": {
      "sha256": "4929a4f73813e5e44d72a77c4ddd1d183ccf8e8e0e7fe9c7880763a0affd9f24",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_context_cf.json": {
      "sha256": "5c05fc201d8070f1a2a2792df0c87467a26c5dac8224a3c3cfdc4cbc2cb94a14",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_context_ch.json": {
      "sha256": "42467da763a8bfa43dce9ce231fc3bdc2f770d54284d599ea35623d1a2c49e42",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_context_ci.json": {
      "sha256": "e559e14109889b884373a2e6cc651f3645289f46c1fda05d9550de35878671c9",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_context_cj.json": {
      "sha256": "19d8e9d6aafd075f3ee2426e9e4853c8cf428d2bebe5439519721b6546236619",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_context_cp.json": {
      "sha256": "d60a95cce94e9f96b07d4590b66e4de92d2c7a748280401011f8df36efb7447f",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_context_cr.json": {
      "sha256": "5afa916a5bbd6b20dbf2ffc5ebe2345730beafb73981cb0f200de01bd04432d6",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_context_cw.json": {
      "sha256": "cf82613880d53be14b7ae6fb54259ed09ead4f95f44a4fc58e3770e99e257428",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_dark_forest_loc_hero.json": {
      "sha256": "de4922b4da9a6102fd6c72deff42d7ee781ae4711478808bac5b1011a6a9d795",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_dark_forest_loc_mage.json": {
      "sha256": "fe4f7147fd42bae23ec778efacc440098afc97960f073636bfac9dbcd65039c6",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_dark_forest_loc_thief.json": {
      "sha256": "ee9afd1b964450e45da5f59b2124fae372714e44063f758fb50db2ae2b9c7653",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_dragon_valley_loc_hero.json": {
      "sha256": "6be7fc46e826df0a435ecde61a541b0e0f45a7a32d42fc02214187a86dd1968c",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_elf_spring_mage.json": {
      "sha256": "36a07f6b83a0777f87498385a6be916071137ec064fb0d5a0bfb2d18b51ab6fe",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_forest_exit_hero.json": {
      "sha256": "22c510dcbef53d31fd3e1130ba02aaab9cce269df2817ec34c68bcc100b1535f",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_forge_hero.json": {
      "sha256": "754dc8100a5a931e3139023c511688130af713363fd0958eb07e4b2558b4deac",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_goblin_fort_chest_choice_thief.json": {
      "sha256": "ba26469a9bae347d694a1865feaa597fadfd21e6a9518203301fe79386d13fdf",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_goblin_fort_first_second_mage.json": {
      "sha256": "f60f3f9216b6e7fc90ddcae2f00dbde3b8594f5d3c77cfc3c22a1aa1ecafb758",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_goblin_fort_healing_circle_mage.json": {
      "sha256": "b25464d64b8c6dd6d7a0014079aac243c9c985d1f84f9005ed14bdd6689b68e8",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_goblin_fort_second_choice_hero.json": {
      "sha256": "918279362e9c2700617ea9849e70c271351f685f095ec15371d8869a3df1608a",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_goblin_fort_second_right_thief.json": {
      "sha256": "ea289b09cb577943f31ca939059fd77fe56b967ec72362e05677e9f7ac71b271",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_goblin_fort_thief.json": {
      "sha256": "6dab3344cc6e0ec92564dcd67f98a91c882414bacc0f02110d878b71414be872",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_goblin_fort_third_gate_hero.json": {
      "sha256": "845e5b6a74ef1829c6fe60c0fc5ab15746481bf32dceb1914f6c9f73e9934efa",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_ian_ice_katana_aftermath_hero.json": {
      "sha256": "bc6195799199897034b6190a7cf6d3a83484756bb2b00330087f6c8955438109",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_ice_elemental_encounter_mage.json": {
      "sha256": "8a9fcce9e9b1ded36a2267f3d05a6cae710a1e50052eff1d4074cb44a8973c50",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_inn_mage.json": {
      "sha256": "5cdf0526b492b43a9e40ddedc9e6e4ad8bc7dc415fec9deaea77170cc4491942",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_item_shop_thief.json": {
      "sha256": "d0eeadbcf4fbe26c3cc60a7085699f9e47427707e662ac534df57fec4a003bfe",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_lost_goblin_crossroads_thief.json": {
      "sha256": "a0a80a97569d6bb6304e5aca1756cfcf5412be9bba2362e3cc8d5f7e5e3a5167",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_magic_shop_mage.json": {
      "sha256": "ae54dedf6ad2d0acdbc4e4d8cd5a049c37dca6536a0ec7181ea07a7edd6c4caa",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_village_approach_thief.json": {
      "sha256": "2a97f7583e2d4bdd61dc642e6c756c071de01695e983a9d449781720dabde494",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_village_frozen_clue_thief.json": {
      "sha256": "a8519476fded43db1b2bcee57e9d553b14d4f5f81793ca0b8006b8587842f279",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_village_mage.json": {
      "sha256": "4e3b2c63e7c1343167cd6fdba98d167526e197b1aea6fb8ee91a590658594e0a",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_xanxus_confrontation_hero.json": {
      "sha256": "d4dc6d1d0c2796c018b4f062f2506a92146de13ee3ebbdd085916b61da9ae157",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "eval/snapshots/v2_xanxus_ultimatum_mage.json": {
      "sha256": "cfeb170c243a656fcdf1f02d4e6bf4b6ecb3ff3fe96cf93e8857f9f5e35cba41",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "host/__init__.py": {
      "sha256": "67c5540ed5ffd4ab154da8a8be8a105bb03e0423045822043b7b03f6fb90956f",
      "last_commit": "13b3dc5741cfa2540e17ed0f8c06e49df18f7f50"
    },
    "host/app.py": {
      "sha256": "adcd478f7ec110f765e17ab7939237a559ba9210c9b649de8c7ed1a8331cfb31",
      "last_commit": "b5fbe460613d108f817ad8b7ec9ea91532375f0c"
    },
    "host/area_retry.py": {
      "sha256": "f00472b86bdb693ed3d459dd1a8995cb87d9eb3a7673a0cffec8a290c4ccfd2b",
      "last_commit": "b0d1838ddfbf9cc56522c0ffe73b633b93550875"
    },
    "host/combat.py": {
      "sha256": "50a386e1054a87c37461b7b99d8fac0fb2726660edc6e505455d68f09e02d9d5",
      "last_commit": "a72e4dba2a177850b6f4cb66828720fe4a1d235f"
    },
    "host/difficulty.py": {
      "sha256": "19f40d9f1c9bb1d32efb6b35850ff129e03fea1e47f8197efd5741102c21e051",
      "last_commit": "af74aa63ee8f2bcf85ddbb0f0aa1abdb4a27e023"
    },
    "host/expand_dragon_scenario.py": {
      "sha256": "6ff159d236bb574172750a813b5bfceae45aac941d8352747bec30f528429203",
      "last_commit": "60aefd5fd14583d628859779a94816fb211d48ae"
    },
    "host/free_actions.py": {
      "sha256": "e519b59e2c2e84c1e4ea11fc3db30c1d146b63176e1c912ef71769c873200f7f",
      "last_commit": "dc2ab65040ea706fb0b8e2d9f5b8e3189c7ed8ac"
    },
    "host/generate_hybrid_scenario.py": {
      "sha256": "7a540cb55a6a127c2f4af8a95bda1d2fbbba4ef9fe7243a1ea3eaa42804d3a23",
      "last_commit": "ec2e5400d0dafaee7e55118bfe68d703fe3badb2"
    },
    "host/gm_contract.py": {
      "sha256": "d2ce2d77b3ad3fe52d34586ab2c2747e199ea46041d45d2677a40faba4764614",
      "last_commit": "ac6c28fd23014dd68bec50a8bc1fb84fd7c1a352"
    },
    "host/intent_resolver.py": {
      "sha256": "3db123ef91e575acfd12806e5273724d683b951c35c3a667b2fb1b9e435dd5d2",
      "last_commit": "2094aaacbf551b7c3612c61a9433e6bf9b2379d4"
    },
    "host/item_mechanics.py": {
      "sha256": "a6b03875884c80d3538d254bf793692736987403156b68d0524566d918de95bd",
      "last_commit": "dc2ab65040ea706fb0b8e2d9f5b8e3189c7ed8ac"
    },
    "host/llm_client.py": {
      "sha256": "7ba77bd680e53b5a7f0ec99022e9274318acd10d50a36775a2e20ca659b37c76",
      "last_commit": "8a48f227e545be1df07ab24c1c70382909261425"
    },
    "host/llm_trace.py": {
      "sha256": "b8a9676b446f339b6448a424f70eccad238f5b1c782358dfce6487fe89b1ccee",
      "last_commit": "ec2e5400d0dafaee7e55118bfe68d703fe3badb2"
    },
    "host/maps.py": {
      "sha256": "2781e1b5c64b23418a21b1e9696017321ea0b77d559cd2a104338f3af6528533",
      "last_commit": "b0d1838ddfbf9cc56522c0ffe73b633b93550875"
    },
    "host/npc_combat.py": {
      "sha256": "b0501676f1f637e5d964f20e2a7f2781d3e1bb523e052520aaef899a985b92f4",
      "last_commit": "6f89d3a6511ad820ee6cef9af0e7d514c5f625f6"
    },
    "host/ollama_tunnel_proxy.py": {
      "sha256": "610a8577914806161a9dc159c5c012d06d9f4396e74912360db2047541c35185",
      "last_commit": "18b3ca14252b17df3c200e742ac173f4e45df642"
    },
    "host/progression.py": {
      "sha256": "46c85c0aab7b9e0b37a5e235055a8bfc5c54b1f429a5bddd589e283a604cb3a5",
      "last_commit": "c72f00867bce2d3235fe503790129c934a669b1c"
    },
    "host/quests.py": {
      "sha256": "4f09bafa903214c8db6aecd4f9e6c7db4665a39f153625ffb47afaedcabf5600",
      "last_commit": "b0d1838ddfbf9cc56522c0ffe73b633b93550875"
    },
    "host/run_server.py": {
      "sha256": "dae199cca8128ca764e0a95e25e5e5632625b9588875d6133fa0ecbf2ed888a1",
      "last_commit": "91497b6b685a525bb43a1f9045ca36249d587849"
    },
    "host/scenario_context.py": {
      "sha256": "78ae6f6eed2e781d8bcfa15842d7f9cbd30fb8e8cf8f92df4001fd4aea65f9e9",
      "last_commit": "35a3cced66a3fd34b3eaaf2fd223b874f97d3dc2"
    },
    "host/scenario_converter.py": {
      "sha256": "0df0edba3af4a8fe4c696ba81ee43ccdf983751e267c3f06ee7d14989c589131",
      "last_commit": "ec2e5400d0dafaee7e55118bfe68d703fe3badb2"
    },
    "host/setup_ollama_models.py": {
      "sha256": "e032d09192066e327eac32c62dc9196e99f2ca7c243de93de34a6149c7775d35",
      "last_commit": "d14aae8cb6eafc8309779961c35f7380d33674c8"
    },
    "host/shops.py": {
      "sha256": "99cd6665772c4315100a433295e66ff0a072165c2cf5b9fdc71465e27fdc43f7",
      "last_commit": "b5fbe460613d108f817ad8b7ec9ea91532375f0c"
    },
    "host/state.py": {
      "sha256": "00024d4f3123a8da6104dd6617141b3197139ff25518e8332e8a53afbd4116b9",
      "last_commit": "20f411687f525077f38bf55b0a5f8c38abe4c9d5"
    },
    "host/status_effects.py": {
      "sha256": "3b757f78c9f9843b5a1e77332368ddcda20193845e4989db2e98356d47688b26",
      "last_commit": "20f411687f525077f38bf55b0a5f8c38abe4c9d5"
    },
    "host/world_state.py": {
      "sha256": "dafb0e8fbc80df9af578dab46ec77e7eda9eb6145190a2dcc04a057884cbe054",
      "last_commit": "fccd1f167674ba37acdb96aa22eef3dc9aa07ccd"
    },
    "scripts/eval/__init__.py": {
      "sha256": "3a2e7fb4c186fa8051a976c9a24a25839ac227e6d299d0571fbbace6bb488a8a",
      "last_commit": "d68113f0b6fa382e61957e14e52a5cb7b4b58e2f"
    },
    "scripts/eval/audit.py": {
      "sha256": "57c4608710d0cea21dfde8b73c395f1be1f3d782efed85aacc3d4b228930e112",
      "last_commit": "52caea89d59b1552fbc19cedb9425baf92a2e069"
    },
    "scripts/eval/benchmark_v2.py": {
      "sha256": "5f2bde60b3a57538ec0f4d4897bae4c9ccd0e16c31ef191a60258163bc6ae6d5",
      "last_commit": "6304d53efabc37888b7a8f863cd28d892d65891c"
    },
    "scripts/eval/cache.py": {
      "sha256": "1adc5776684770ab7c115dc3811186ade2310f9ce0737636e8712186f329b838",
      "last_commit": "1f5426067e24cde3d37376eca9054487f716ed68"
    },
    "scripts/eval/generate_candidates.py": {
      "sha256": "14face5ba9e93e3c29a973ae2c058ad6bf53bbed617624ec6c0dafe04763f751",
      "last_commit": "fe71d0469b3a3c1c12c74e722785d6232ba06e6b"
    },
    "scripts/eval/heldout.py": {
      "sha256": "4e493898e2e44b5c429a6a35fc0374f0df988375d92502c5cdaa843e525b3e6b",
      "last_commit": "0a1fdae10ee5e0b49166d2df59834fab8d640526"
    },
    "scripts/eval/metrics.py": {
      "sha256": "ee4fb9546eaf436092906ae4eb5a235ee33f3916534e6f219ad3a2cfb3da64a1",
      "last_commit": "fc853ca394dbf922164d6c42bb30c00bdaa4dfb0"
    },
    "scripts/eval/paper_common.py": {
      "sha256": "f89f86b20691590847fb8f400522b5be484f938f48f4f5eb58a64fa5478038d7",
      "last_commit": "0a1fdae10ee5e0b49166d2df59834fab8d640526"
    },
    "scripts/eval/requests.py": {
      "sha256": "00ef91c88c99345c25ba8300000be7752fc99d4c7353f08adf8aff2a746730e3",
      "last_commit": "ec2e5400d0dafaee7e55118bfe68d703fe3badb2"
    },
    "scripts/eval/run.py": {
      "sha256": "4ccc6b7d78c1e45d46cd11d09e9a001f19b3b7b7e4a4910e063469b85b2d36b2",
      "last_commit": "b0d1838ddfbf9cc56522c0ffe73b633b93550875"
    },
    "scripts/eval/snapshots.py": {
      "sha256": "cde6d4257825e169bb81bcb9dd7ef38c080c9814f833095df83284f58da8f14e",
      "last_commit": "d68113f0b6fa382e61957e14e52a5cb7b4b58e2f"
    },
    "scripts/eval/variants.py": {
      "sha256": "a1525ddf1736585c5c101884a8469177412d09902620e191dbd98cec2fb25a60",
      "last_commit": "ac6c28fd23014dd68bec50a8bc1fb84fd7c1a352"
    },
    "scripts/evaluate_free_actions.py": {
      "sha256": "2b71baeb89eb0502d30bb87e120781545a392e627888fd0ad0f1b19b7f8bde48",
      "last_commit": "d68113f0b6fa382e61957e14e52a5cb7b4b58e2f"
    }
  },
  "default_system_prompt_sha256": "0223af080e40662ffe3e7e9b1d17151aa67dd582f078fa628c8c7fbc08efd5ad",
  "planner_schema_sha256": "51d05dc24701e4bd109aadd908c2aa14984ded8f084e53a29648340a634c2c1f",
  "commitment": "Generate inputs only after registration. One formal attempt, no relabeling or primary rescoring after results. Errors reported separately.",
  "provenance": "Input slots only; argon authors Japanese inputs; design reviews labels under LABELING.md.",
  "workspace_note": "File hashes (text files hashed with LF line endings), including uncommitted workspace files, are authoritative; commit alone is insufficient."
}
```
