# Extraction eval results

50 posts from `hn_jobs.gold.eval_sample`, labels in `eval/labels.jsonl` (48 job posts + 2 non-job comments).

| metric | ai_extract@v1 | gpt-oss-120b@v1 | gpt-oss-120b@v2 | llama-3.3-70b@v1 |
|---|---|---|---|---|
| parsed | 100% | 100% | 100% | 100% |
| is_job_post | 100% | 98% | 100% | 100% |
| company | 100% | 98% | 98% | 100% |
| remote_policy | 96% | 94% | 92% | 94% |
| remote_policy (unambiguous) | 98% | 98% | 98% | 96% |
| seniority (exact set) | 79% | 88% | 94% | 81% |
| seniority (jaccard) | 88% | 95% | 97% | 91% |
| salary | 100% | 98% | 100% | 94% |
| salary (posts with pay) | 100% | 94% | 100% | 88% |
| visa_sponsorship | 96% | 100% | 100% | 100% |
| equity | 100% | 100% | 100% | 100% |
| employment_types | 85% | 90% | 96% | 62% |
| skills precision | 78% | 87% | 98% | 70% |
| skills recall | 96% | 91% | 100% | 92% |
| skills F1 | 86% | 89% | 99% | 79% |

### ai_extract@v1 misses
- **seniority** (10): (42578533, ['lead', 'mid'], ['lead', 'mid', 'senior']); (43875195, ['senior', 'staff+'], ['staff+']); (44765821, ['lead', 'senior', 'staff+'], ['lead', 'staff+']); (45441456, ['lead', 'senior', 'unspecified'], ['lead', 'manager', 'senior']); (45476407, ['manager', 'senior', 'staff+'], ['manager', 'senior', 'staff+', 'unspecified']); (45800956, ['unspecified'], ['staff+']); (46110948, ['unspecified'], ['staff+']); (47220359, ['staff+', 'unspecified'], ['unspecified']); (48363775, ['senior', 'staff+'], ['staff+']); (48365480, ['intern', 'unspecified'], ['staff+'])
- **skills (extra)** (15): (44758408, ['genai', 'nlp']); (44761865, ['abtesting', 'causalinference']); (44765821, ['rest']); (44765950, ['aimodels']); (45800956, ['ai', 'handwritingrecognition', 'knowledgegraphs', 'ocr']); (46110948, ['aipipelines']); (46153361, ['cloudinfrastructure', 'llms', 'restapis']); (46509990, ['containerorchestration', 'loadbalancing', 'monitoring', 'reverseproxyconfiguration', 'vpsadministration']); (46594737, ['git', 'llm']); (48040612, ['node', 'qvac']); (48358258, ['3d', 'cad', 'computervision', 'photogrammetry', 'slam']); (48753597, ['aiml', 'browserextensions']); (48893278, ['netframework48', 'vue2']); (49523808, ['raft']); (49924972, ['kubernetes', 'openstack', 'paxos'])
- **remote_policy** (2): (45441637, 'hybrid', 'onsite'); (49924972, 'onsite', 'remote')
- **skills (missed)** (4): (45441637, ['remix']); (46509990, ['pothos']); (48893278, ['netframework', 'vue']); (49523808, ['react'])

### gpt-oss-120b@v1 misses
- **seniority** (6): (42578533, ['lead', 'mid'], ['lead', 'mid', 'unspecified']); (43875195, ['senior', 'staff+'], ['staff+']); (44765821, ['lead', 'senior', 'staff+'], ['lead', 'senior']); (47220359, ['staff+', 'unspecified'], ['unspecified']); (48365480, ['intern', 'unspecified'], ['intern']); (49156716, ['lead', 'manager', 'unspecified'], ['lead', 'unspecified'])
- **remote_policy** (3): (44759963, 'onsite', 'unspecified'); (46149969, 'remote', 'hybrid'); (49523808, 'remote', 'hybrid')
- **skills (extra)** (8): (44765821, ['rest']); (46110948, ['superset']); (46153361, ['clover', 'square', 'toast']); (48040612, ['node']); (48358258, ['3d', 'cad', 'computervision', 'geomatics', 'photogrammetry', 'slam']); (48753597, ['browserextensions', 'llm', 'machinelearning']); (49523808, ['raft']); (49924972, ['kubernetes', 'openstack'])
- **salary** (1): (45447595, (100000, None, 'GBP', 'year'), (100000, 100000, None, 'year'))
- **skills (missed)** (3): (46110948, ['supabase']); (46509990, ['babylon', 'bullmq', 'fastify', 'graphql', 'maplibre', 'postgresql', 'pothos', 'react', 'redis', 'typescript']); (48893278, ['tsql'])
- **company** (1): (46509990, 'Buildplace', '')

### gpt-oss-120b@v2 misses
- **seniority** (3): (42578533, ['lead', 'mid'], ['lead', 'manager', 'mid']); (47220359, ['staff+', 'unspecified'], ['unspecified']); (48365480, ['intern', 'unspecified'], ['intern'])
- **remote_policy** (4): (44759963, 'onsite', 'unspecified'); (46149969, 'remote', 'hybrid'); (49523808, 'remote', 'hybrid'); (49924972, 'onsite', 'remote')
- **company** (1): (46509990, 'Buildplace', 'Form Follows You GmbH')
- **skills (extra)** (2): (49523808, ['raft']); (49924972, ['kubernetes', 'openstack'])

### llama-3.3-70b@v1 misses
- **seniority** (9): (42578533, ['lead', 'mid'], ['senior']); (43875195, ['senior', 'staff+'], ['staff+']); (44759963, ['mid', 'senior'], ['mid']); (44765821, ['lead', 'senior', 'staff+'], ['lead', 'staff+']); (45441456, ['lead', 'senior', 'unspecified'], ['lead', 'senior']); (47220359, ['staff+', 'unspecified'], ['unspecified']); (48040612, ['lead', 'unspecified'], ['lead', 'senior', 'unspecified']); (48365480, ['intern', 'unspecified'], ['unspecified']); (49156716, ['lead', 'manager', 'unspecified'], ['lead', 'unspecified'])
- **skills (extra)** (24): (43244119, ['ai']); (43875195, ['ruby']); (44167902, ['ml']); (44758408, ['genai', 'nlp']); (44759963, ['ai', 'promptengineering']); (44761865, ['abtesting']); (44765821, ['rest']); (45168091, ['ai', 'ml']); (45441637, ['remixreact']); (45800956, ['ai', 'chromebook', 'handwritingrecognition', 'knowledgegraphs', 'mathequations', 'ocr']); (46153361, ['clover', 'llms', 'restapis', 'square', 'toast']); (46495610, ['ai', 'zoom']); (46594737, ['git', 'ide', 'llms']); (47220359, ['containerorchestration', 'ml']); (47610050, ['ai']); (48040612, ['node']); (48358258, ['3d', 'cad', 'computervision', 'geomatics', 'photogrammetry', 'slam']); (48363775, ['ai']); (48365480, ['hardwareadjacentsystems', 'softwareengineering']); (48753597, ['aiml', 'browserextensions']); (48893278, ['aspnetmvcrazor', 'netframework48', 'sqlservertsql', 'vue2']); (49157182, ['webdata']); (49523808, ['raft']); (49924972, ['kubernetes', 'openstack', 'paxos'])
- **remote_policy** (3): (44758408, 'remote', 'hybrid'); (46149969, 'remote', 'hybrid'); (49523808, 'remote', 'hybrid')
- **skills (missed)** (5): (45441637, ['react', 'remix']); (46110948, ['tanstack']); (48753597, ['macos']); (48893278, ['aspnetmvc', 'netframework', 'razor', 'sqlserver', 'tsql', 'vue']); (49523808, ['react'])
- **salary** (3): (45447595, (100000, None, 'GBP', 'year'), (100000, 200000, 'GBP', 'year')); (46113455, (None, 140000, 'CAD', 'year'), (140000, 140000, 'CAD', 'year')); (46495610, (None, None, None, None), (50000, 100000, 'USD', 'year'))
