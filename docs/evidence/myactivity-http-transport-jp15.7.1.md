# Original MyActivity HTTP Transport — exact JP 15.7.1

Status: static transport call graph proven; product interception still disabled.

Machine-readable companion:
`docs/evidence/myactivity-http-transport-jp15.7.1.json`.

## Result

The original JP 15.7.1 network path is much narrower than the native endpoint
list initially suggested.

`MyActivity.newHttpRequest(...)` does not drop directly into an opaque native
TLS client. Its exact DEX body:

1. constructs `java.net.URL`;
2. constructs an obfuscated request object `La32;`;
3. allocates/increments a request handle;
4. stores it in `MyActivity.mRequestHandles`;
5. calls `La32.run(...)`;
6. returns the request handle.

`La32.run(...)` creates a `java.lang.Thread` around `Lz22;`.

The exact `Lz22.run()` body then uses ordinary Android/Java networking:

- `URL.openConnection()`;
- connect/read timeout setters;
- `HttpURLConnection.setRequestMethod()`;
- `CookieManager`;
- request headers;
- optional output body stream;
- `HttpURLConnection.getResponseCode()`;
- response headers;
- input/error streams;
- direct `ByteBuffer` chunks;
- original static native response callbacks;
- disconnect.

The response path returns to the existing Battle Cats native engine through:

- `MyActivity.onResponseCodeHeaders(...)`
- `MyActivity.onResponseData(...)`
- `MyActivity.onResponseFinish(...)`
- error/fallback `MyActivity.newResponse(...)`

## Exact code fingerprints

| Method | code_off | instruction SHA-256 |
| --- | ---: | --- |
| `MyActivity.isNetworkAvailable` | `0x45eb20` | `536588a2c61fbf437769573b7581cd31433144a2b1355ccb4e5ec71d6c2e4bd4` |
| `MyActivity.newHttpRequest` | `0x45fc58` | `14f896e5b42b8e5b8ab50f756bdc79ad44614325eb153ab99ffcdafb98c70a80` |
| `La32.run` | `0x1f1968` | `b1a8679be3ccf9deadf5a5ef6eca2730220c4414ef08064e12b3f1220ef547e7` |
| `Lz22.run` | `0x1f11c0` | `ad74dcde42dcfa2533de3f57b1b86a04d46326ce5c2c90ac46b4db3c9a669d7a` |
| `Lz22.a` | `0x1f1120` | `b03f69b5a8187bee470b7fdbcee8416e3a01b667f080f37a2042786e3efd1abe` |

These hashes let a future static Java bridge patch fail closed if the anchored
method body drifts.

## Network availability

`MyActivity.isNetworkAvailable()` is also ordinary Java:

```text
"connectivity"
 -> Context.getSystemService
 -> ConnectivityManager.getActiveNetworkInfo
 -> NetworkInfo.isConnectedOrConnecting
```

This matters because offline mode may eventually need to distinguish
"Battle Cats service is locally satisfied" from "Android has internet".

It does **not** justify forcing the method true globally yet.

## Preferred product seam

The leading design is now:

```text
original native caller
       |
       v
MyActivity.newHttpRequest
       |
       +-- recognized Kneekura-local request
       |      -> local provider
       |      -> original onResponse* callbacks
       |
       +-- unrecognized request
              -> exact original newHttpRequest body
              -> original HttpURLConnection transport
```

This is better than hooking sockets, TLS or every endpoint separately because:

- original native callers stay unchanged;
- original request ids stay meaningful;
- original response callbacks stay unchanged;
- original scenes stay unchanged;
- one feature gate can fall through to the exact original method.

## Remaining gate

Static structure is now high-confidence, but we still do not know every
endpoint's exact request/response semantic contract.

The isolated research trace remains required to capture at least one harmless
original request and its callback sequence before we implement a shipping
selective local provider wrapper.

Until then the provider ABI remains disconnected.
