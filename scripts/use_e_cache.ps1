# ColdChain-QA — 缓存全部落在 E 盘（勿改到 C:）
$env:PIP_CACHE_DIR = "E:\Learning\ColdChain-QA\.cache\pip"
$env:HF_HOME = "E:\Learning\ColdChain-QA\.cache\huggingface"
$env:HUGGINGFACE_HUB_CACHE = "E:\Learning\ColdChain-QA\.cache\huggingface\hub"
$env:TRANSFORMERS_CACHE = "E:\Learning\ColdChain-QA\.cache\huggingface\transformers"
$env:TORCH_HOME = "E:\Learning\ColdChain-QA\.cache\torch"
$env:TMP = "E:\Learning\ColdChain-QA\.cache\tmp"
$env:TEMP = "E:\Learning\ColdChain-QA\.cache\tmp"
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null

$env:HF_ENDPOINT = 'https://hf-mirror.com'
