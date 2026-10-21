# Extraction eval results

50 posts from `hn_jobs.gold.eval_sample`, labels in `eval/labels.jsonl` (48 job posts + 2 non-job comments).

| metric | ai_extract@v4 | gemma-3-12b@v4 | gpt-oss-120b@v4 | gpt-oss-20b@v4 | llama-3.3-70b@v4 | llama-4-maverick@v4 | qwen3-next-80b@v4 | qwen35-122b@v4 |
|---|---|---|---|---|---|---|---|---|
| parsed | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 86% |
| is_job_post | 100% | 98% | 100% | 98% | 100% | 100% | 100% | 100% |
| company | 98% | 100% | 98% | 98% | 100% | 100% | 100% | 100% |
| remote_policy | 94% | 75% | 94% | 88% | 88% | 88% | 83% | 100% |
| remote_policy (unambiguous) | 96% | 78% | 98% | 91% | 89% | 89% | 84% | 100% |
| seniority (exact set) | 85% | 79% | 90% | 88% | 85% | 88% | 83% | 90% |
| seniority (jaccard) | 89% | 88% | 94% | 92% | 92% | 92% | 89% | 95% |
| salary | 100% | 79% | 100% | 98% | 92% | 100% | 100% | 100% |
| salary (posts with pay) | 100% | 88% | 100% | 94% | 88% | 100% | 100% | 100% |
| visa_sponsorship | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 100% |
| equity | 100% | 98% | 100% | 98% | 100% | 96% | 100% | 100% |
| employment_types | 88% | 75% | 96% | 94% | 69% | 62% | 62% | 95% |
| countries (exact set) | 94% | 90% | 94% | 96% | 83% | 96% | 90% | 100% |
| countries (jaccard) | 94% | 91% | 96% | 96% | 83% | 96% | 90% | 100% |
| skills precision | 93% | 66% | 96% | 92% | 77% | 92% | 75% | 97% |
| skills recall | 95% | 98% | 99% | 90% | 95% | 97% | 95% | 98% |
| skills F1 | 94% | 79% | 97% | 91% | 85% | 95% | 84% | 97% |

### ai_extract@v4 misses
- **seniority** (7): (42578533, ['lead', 'mid'], ['lead', 'senior', 'unspecified']); (45441456, ['lead', 'senior', 'unspecified'], ['lead', 'manager', 'senior']); (45441637, ['staff+', 'unspecified'], ['staff+']); (45800956, ['unspecified'], ['staff+']); (46110948, ['unspecified'], ['staff+']); (48040612, ['lead', 'unspecified'], ['lead', 'manager', 'unspecified']); (48365480, ['intern', 'unspecified'], ['staff+'])
- **countries** (3): (43244119, ['US'], []); (44765821, [], ['US']); (48753597, [], ['US'])
- **skills (missed)** (5): (44765821, ['graphql']); (45441637, ['remix']); (46509990, ['pothos']); (48893278, ['netframework', 'razor', 'vue']); (49523808, ['react'])
- **remote_policy** (3): (46149969, 'remote', 'hybrid'); (46509990, 'unspecified', 'onsite'); (49924972, 'onsite', 'remote')
- **skills (extra)** (4): (46495610, ['zoom']); (48040612, ['hadron', 'node', 'qvac']); (48893278, ['aspnetrazor', 'netframework48', 'vue2']); (49924972, ['kubernetes', 'openstack'])
- **company** (1): (46509990, 'Buildplace', 'Form Follows You GmbH')

### gemma-3-12b@v4 misses
- **skills (extra)** (27): (42576683, ['react']); (43244119, ['ai', 'userinterviews']); (44167902, ['ml']); (44759963, ['ai', 'codereview', 'promptengineering']); (44761865, ['abtesting', 'causalinference']); (44765821, ['rest']); (44765950, ['ai', 'machinelearning']); (45168091, ['ai', 'dataprocessing']); (45447595, ['ui', 'ux']); (45800956, ['ai', 'handwritingrecognition', 'ocr']); (46110948, ['ai']); (46153361, ['aws', 'clover', 'gcp', 'generativeai', 'llms', 'rest', 'square', 'toast']); (46495610, ['ai', 'aws', 'graphql', 'kubernetes', 'postgresql', 'python', 'react', 'zoom']); (46594737, ['design', 'engineering', 'ui']); (47220359, ['containerorchestration', 'ml']); (47604264, ['machinelearning', 'nlp']); (47610050, ['ai']); (48040612, ['node', 'react']); (48358258, ['3d', 'cad', 'computervision', 'geomatics', 'photogrammetry', 'slam']); (48363775, ['ai', 'fintech', 'healthcare']); (48365480, ['hardware', 'softwareengineering']); (48753597, ['aiml', 'browserextensions']); (48893278, ['vue2']); (49156716, ['posthog']); (49157182, ['cloud', 'genai', 'webdata']); (49523808, ['raft']); (49924972, ['kubernetes', 'openstack', 'paxos'])
- **remote_policy** (12): (42578533, 'hybrid', 'onsite'); (43245898, 'remote', 'hybrid'); (44161465, 'remote', 'hybrid'); (44758408, 'remote', 'hybrid'); (44759963, 'onsite', 'unspecified'); (44765950, 'remote', 'hybrid'); (45447595, 'hybrid', 'onsite'); (46149969, 'remote', 'hybrid'); (46495610, 'remote', 'hybrid'); (47220359, 'remote', 'hybrid'); (47604264, 'remote', 'hybrid'); (49523808, 'remote', 'hybrid')
- **seniority** (10): (42578533, ['lead', 'mid'], ['mid', 'unspecified']); (44167902, ['unspecified'], ['mid']); (45441456, ['lead', 'senior', 'unspecified'], ['lead', 'senior']); (45800572, ['lead', 'senior', 'staff+'], ['lead', 'senior', 'staff+', 'unspecified']); (47220359, ['staff+', 'unspecified'], ['unspecified']); (47604264, ['senior'], ['mid', 'senior']); (48040612, ['lead', 'unspecified'], ['lead', 'manager', 'senior', 'unspecified']); (48365480, ['intern', 'unspecified'], ['unspecified']); (49924509, ['senior', 'unspecified'], ['mid', 'senior', 'unspecified']); (49924972, ['unspecified'], ['mid'])
- **countries** (5): (42583497, [], ['EU']); (42632472, [], ['GB']); (44765821, [], ['US']); (46149969, ['GB'], ['DE', 'GB']); (48363775, ['US'], [])
- **salary** (10): (44758408, (165000, 215000, 'CAD', 'year'), (165000, 230000, 'CAD', 'year')); (45168091, (None, None, None, None), (150000, 230000, 'USD', 'year')); (45447595, (100000, None, 'GBP', 'year'), (100000, 100000, 'GBP', 'year')); (46110948, (None, None, None, None), (150000, 230000, 'USD', 'year')); (46153361, (None, None, None, None), (150000, 230000, 'USD', 'year')); (46495610, (None, None, None, None), (150000, 230000, 'USD', 'year')); (47220359, (None, None, None, None), (150000, 230000, 'USD', 'year')); (47610050, (None, None, None, None), (100000, 200000, 'USD', 'year')); (48757527, (None, None, None, None), (150000, 230000, 'USD', 'year')); (49156716, (None, None, None, None), (100000, 200000, 'USD', 'year'))
- **skills (missed)** (2): (45441637, ['remix']); (48893278, ['vue'])

### gpt-oss-120b@v4 misses
- **countries** (3): (43245898, ['GB', 'US'], ['GB']); (44758408, ['CA', 'US'], ['CA']); (44765821, [], ['US'])
- **skills (extra)** (4): (43875195, ['ruby']); (48753597, ['llm', 'machinelearning']); (49523808, ['raft']); (49924972, ['kubernetes', 'openstack'])
- **remote_policy** (3): (44759963, 'onsite', 'unspecified'); (46149969, 'remote', 'hybrid'); (49523808, 'remote', 'hybrid')
- **skills (missed)** (1): (44765821, ['graphql'])
- **seniority** (5): (45800956, ['unspecified'], ['senior']); (47220359, ['staff+', 'unspecified'], ['unspecified']); (47604264, ['senior'], ['senior', 'unspecified']); (48040612, ['lead', 'unspecified'], ['lead', 'manager', 'unspecified']); (48365480, ['intern', 'unspecified'], ['intern'])
- **company** (1): (46509990, 'Buildplace', 'Form Follows You GmbH')

### gpt-oss-20b@v4 misses
- **seniority** (6): (42578533, ['lead', 'mid'], ['lead', 'mid', 'unspecified']); (44758408, ['manager', 'senior', 'staff+'], ['unspecified']); (45441456, ['lead', 'senior', 'unspecified'], ['lead', 'manager', 'senior']); (47220359, ['staff+', 'unspecified'], ['unspecified']); (48365480, ['intern', 'unspecified'], ['unspecified']); (48893278, ['mid'], ['unspecified'])
- **skills (extra)** (6): (43875195, ['ruby']); (44761865, ['abtesting', 'causalinference']); (46153361, ['clover', 'square', 'toast']); (48753597, ['browserextensions']); (48893278, ['aspnetmvcrazor', 'netframework48', 'vue2']); (49523808, ['raft'])
- **company** (1): (44758408, 'Clio', '')
- **remote_policy** (6): (44758408, 'remote', 'unspecified'); (44759963, 'onsite', 'unspecified'); (45441637, 'hybrid', 'onsite'); (45447595, 'hybrid', 'remote'); (46149969, 'remote', 'hybrid'); (49523808, 'remote', 'hybrid')
- **salary** (1): (44758408, (165000, 215000, 'CAD', 'year'), (None, None, None, None))
- **countries** (2): (44758408, ['CA', 'US'], []); (44765821, [], ['US'])
- **skills (missed)** (4): (44758408, ['aws', 'kubernetes', 'mysql', 'python', 'ruby', 'rubyonrails', 'terraform']); (46509990, ['pothos']); (48753597, ['macos']); (48893278, ['aspnetmvc', 'netframework', 'razor', 'vue'])

### llama-3.3-70b@v4 misses
- **skills (extra)** (22): (42576683, ['react']); (43244119, ['ai']); (43875195, ['ruby']); (44167902, ['ml']); (44758408, ['genai', 'nlp']); (44759963, ['ai']); (44761865, ['abtesting', 'causalinference']); (44765821, ['rest']); (45168091, ['ai', 'ml']); (45441637, ['remixreact']); (45800956, ['ai', 'chromebook', 'ocr']); (46113455, ['microsoftword']); (46153361, ['clover', 'llms', 'restapis', 'square', 'toast']); (46495610, ['ai', 'zoom']); (46594737, ['git', 'ide', 'llms']); (47220359, ['ml']); (47610050, ['ai']); (48040612, ['node']); (48365480, ['hardwareadjacentsystems', 'softwareengineering']); (48753597, ['aiml', 'browserextensions']); (48893278, ['vue2']); (49924972, ['kubernetes', 'openstack', 'paxos'])
- **seniority** (7): (42578533, ['lead', 'mid'], ['manager', 'senior']); (45441456, ['lead', 'senior', 'unspecified'], ['lead', 'unspecified']); (46495610, ['senior', 'staff+', 'unspecified'], ['senior', 'unspecified']); (47220359, ['staff+', 'unspecified'], ['unspecified']); (48040612, ['lead', 'unspecified'], ['lead', 'senior', 'unspecified']); (48365480, ['intern', 'unspecified'], ['unspecified']); (49156716, ['lead', 'manager', 'unspecified'], ['unspecified'])
- **countries** (8): (42583497, [], ['EU']); (42632472, [], ['GB']); (44761865, [], ['AR', 'BR', 'CA', 'DE', 'FR', 'GB', 'US']); (44765821, [], ['US']); (45800572, [], ['AR', 'BO', 'BR', 'CL', 'CO', 'CR', 'CU', 'DO', 'EC', 'GT', 'GY', 'HN', 'HT', 'MX', 'NI', 'PA', 'PE', 'PR', 'PY', 'SV', 'TT', 'UY', 'VE']); (48358258, [], ['AR', 'BO', 'BR', 'CL', 'CO', 'CR', 'CU', 'DO', 'EC', 'GT', 'GY', 'HN', 'MX', 'NI', 'PA', 'PE', 'PR', 'PY', 'SV', 'TT', 'UY', 'VE']); (48365480, [], ['US']); (48753597, [], ['US'])
- **remote_policy** (6): (43245898, 'remote', 'hybrid'); (44161465, 'remote', 'hybrid'); (44758408, 'remote', 'hybrid'); (44765950, 'remote', 'hybrid'); (46149969, 'remote', 'hybrid'); (49523808, 'remote', 'hybrid')
- **salary** (4): (43245898, (60000, 160000, 'GBP', 'year'), (80000, 160000, 'GBP', 'year')); (45443875, (None, None, None, None), (150000, 200000, 'USD', 'year')); (45447595, (100000, None, 'GBP', 'year'), (100000, 200000, 'GBP', 'year')); (46495610, (None, None, None, None), (50000.0, 100000.0, 'USD', 'year'))
- **skills (missed)** (5): (45441637, ['react', 'remix']); (46110948, ['tanstack']); (46509990, ['pothos']); (48753597, ['macos']); (48893278, ['razor', 'vue'])

### llama-4-maverick@v4 misses
- **skills (extra)** (9): (42576683, ['react']); (44765821, ['rest']); (45800956, ['ai']); (46153361, ['rest']); (46495610, ['ai', 'zoom']); (48040612, ['node']); (48363775, ['ai']); (49523808, ['raft']); (49924972, ['kubernetes', 'openstack'])
- **seniority** (6): (42578533, ['lead', 'mid'], ['lead', 'manager', 'mid']); (45800956, ['unspecified'], ['senior']); (46110948, ['unspecified'], ['senior']); (46495610, ['senior', 'staff+', 'unspecified'], ['junior', 'senior', 'staff+']); (47220359, ['staff+', 'unspecified'], ['unspecified']); (48040612, ['lead', 'unspecified'], ['lead', 'senior', 'unspecified'])
- **remote_policy** (6): (43875195, 'remote', 'hybrid'); (44758408, 'remote', 'hybrid'); (44765950, 'remote', 'hybrid'); (46149969, 'remote', 'hybrid'); (46509990, 'unspecified', 'onsite'); (49523808, 'remote', 'hybrid')
- **skills (missed)** (4): (44758408, ['terraform']); (45441637, ['remix']); (48358258, ['ios']); (48893278, ['razor'])
- **countries** (2): (44765821, [], ['US']); (48365480, [], ['US'])

### qwen3-next-80b@v4 misses
- **skills (extra)** (15): (42576683, ['react']); (43244119, ['ai']); (44167902, ['ml']); (44759963, ['ai', 'developertooling', 'promptengineering']); (44765821, ['rest']); (45168091, ['aws', 'kubernetes', 'python', 'pytorch', 'sql', 'tensorflow']); (45800956, ['ai', 'handwritingrecognition', 'knowledgegraphs', 'mathematicalreasoning', 'ocr']); (46495610, ['aws', 'javascript', 'kubernetes', 'postgresql', 'python', 'react']); (46509990, ['containerorchestration', 'loadbalancing', 'monitoring', 'reverseproxy', 'vpsadministration']); (48040612, ['node']); (48365480, ['hardwareadjacentsystems', 'softwareengineering']); (48753597, ['ai', 'browserextensions', 'ml']); (48893278, ['aspnet', 'mvc', 'webforms']); (49157182, ['web']); (49924972, ['kubernetes', 'paxos'])
- **remote_policy** (8): (42578533, 'hybrid', 'onsite'); (44758408, 'remote', 'hybrid'); (45441637, 'hybrid', 'onsite'); (45813360, 'hybrid', 'onsite'); (46149969, 'remote', 'hybrid'); (46509990, 'unspecified', 'onsite'); (49523808, 'remote', 'hybrid'); (49924509, 'hybrid', 'onsite')
- **seniority** (8): (42578533, ['lead', 'mid'], ['lead', 'manager', 'senior']); (45441456, ['lead', 'senior', 'unspecified'], ['lead', 'senior']); (45441637, ['staff+', 'unspecified'], ['senior', 'staff+']); (45800956, ['unspecified'], ['senior']); (46110948, ['unspecified'], ['senior']); (47220359, ['staff+', 'unspecified'], ['unspecified']); (48040612, ['lead', 'unspecified'], ['lead', 'senior', 'unspecified']); (48365480, ['intern', 'unspecified'], ['unspecified'])
- **countries** (5): (42583497, [], ['EU']); (42632472, [], ['AD', 'AT', 'BE', 'BG', 'CH', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI', 'FR', 'GB', 'GR', 'HU', 'IE', 'IS', 'IT', 'LI', 'LT', 'LV', 'MC', 'NL', 'NO', 'PL', 'PT', 'RO', 'RU', 'SE', 'SK', 'SM', 'TR', 'UA', 'VA']); (44765821, [], ['US']); (46149969, ['GB'], ['AT', 'BE', 'BG', 'CH', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI', 'FR', 'GB', 'GR', 'HR', 'HU', 'IT', 'LT', 'LV', 'NL', 'NO', 'PL', 'PT', 'RO', 'RU', 'SE', 'SI', 'SK', 'TR', 'UA']); (48358258, [], ['AR', 'BO', 'BR', 'CL', 'CO', 'CR', 'CU', 'DO', 'EC', 'GT', 'GY', 'HN', 'HT', 'MX', 'NI', 'PA', 'PE', 'PR', 'PY', 'SR', 'SV', 'UY', 'VE'])
- **skills (missed)** (5): (43875195, ['postgresql']); (45441637, ['remix']); (46113455, ['office']); (48893278, ['aspnetmvc', 'aspnetwebforms', 'razor']); (49523808, ['react'])

### qwen35-122b@v4 misses
- **seniority** (4): (42578533, ['lead', 'mid'], ['lead', 'manager', 'senior']); (45441456, ['lead', 'senior', 'unspecified'], ['lead', 'manager', 'senior']); (48040612, ['lead', 'unspecified'], ['lead', 'manager', 'unspecified']); (48365480, ['intern', 'unspecified'], ['unspecified'])
- **skills (extra)** (3): (43875195, ['ruby']); (48753597, ['browserextensions']); (49924972, ['kubernetes', 'openstack'])
- **skills (missed)** (2): (46509990, ['pothos']); (48893278, ['razor'])
