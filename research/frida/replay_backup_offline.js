'use strict';

import Java from 'frida-java-bridge';

/*
 * Research-only selective local replay for exact JP 15.7.1.
 *
 * Scope is intentionally tiny:
 *   GET https://nyanko-backups.ponosgames.com/?...
 *   timeout 10, empty request-header map, no body, empty String[], flags false,false
 *
 * The replay mirrors the observed airplane-mode fallback:
 *   request id allocated/stored like original newHttpRequest
 *   -> GLSurfaceView.queueEvent(...)
 *   -> MyActivity.newResponse(id, 0, url, "{}", null, true)
 *
 * Every unrecognized request calls the exact original newHttpRequest overload.
 * This script is research-only and must never ship in Personal/Practice.
 */

Java.perform(function () {
    const TAG = 'KNEEKURA_REPLAY';
    const MyActivity = Java.use('jp.co.ponos.battlecats.MyActivity');
    const URL = Java.use('java.net.URL');
    const IntegerClass = Java.use('java.lang.Integer');
    const JavaMap = Java.use('java.util.Map');
    const Runnable = Java.use('java.lang.Runnable');
    const Request = Java.use('a32');

    function safeString(value) {
        try {
            if (value === null || value === undefined) return null;
            return String(value);
        } catch (_) {
            return '<unprintable>';
        }
    }

    function log(kind, fields) {
        const payload = fields || {};
        payload.kind = kind;
        payload.source = 'kneekura-jp15.7.1-backup-offline-replay';
        const line = 'KNEEKURA_REPLAY ' + JSON.stringify(payload);
        try {
            Java.use('android.util.Log').i(TAG, line);
        } catch (_) {
            console.log(line);
        }
    }

    function field(klass, name) {
        const result = klass.getDeclaredField(name);
        result.setAccessible(true);
        return result;
    }

    function exactBackupFamily(method, url, timeout, headers, body, strings, flag1, flag2) {
        try {
            if (safeString(method) !== 'GET') return false;
            if (Number(timeout) !== 10) return false;
            if (body !== null) return false;
            if (Boolean(flag1) || Boolean(flag2)) return false;
            if (headers === null || Number(headers.size()) !== 0) return false;
            if (strings === null || Number(strings.length) !== 0) return false;

            const parsed = URL.$new(url);
            return safeString(parsed.getProtocol()) === 'https'
                && safeString(parsed.getHost()) === 'nyanko-backups.ponosgames.com'
                && safeString(parsed.getPath()) === '/';
        } catch (error) {
            log('classifier_error', { error: safeString(error) });
            return false;
        }
    }

    const ReplayRunnable = Java.registerClass({
        name: 'jp.kn.trace.battlecats.KneekuraBackupOfflineReplay',
        implements: [Runnable],
        fields: {
            requestId: 'int',
            requestUrl: 'java.lang.String'
        },
        methods: {
            $init: [{
                returnType: 'void',
                argumentTypes: ['int', 'java.lang.String'],
                implementation: function (requestId, requestUrl) {
                    this.requestId.value = requestId;
                    this.requestUrl.value = requestUrl;
                }
            }],
            run: function () {
                const requestId = this.requestId.value;
                const requestUrl = this.requestUrl.value;
                log('local_response_enter', { request_id: requestId });
                MyActivity.newResponse(
                    requestId,
                    0,
                    requestUrl,
                    '{}',
                    null,
                    true
                );
                log('local_response_return', { request_id: requestId });
            }
        }
    });

    const newHttp = MyActivity.newHttpRequest.overload(
        'java.lang.String',
        'java.lang.String',
        'float',
        'java.util.HashMap',
        'java.nio.ByteBuffer',
        '[Ljava.lang.String;',
        'boolean',
        'boolean'
    );

    newHttp.implementation = function (
        method,
        url,
        timeout,
        headers,
        body,
        strings,
        flag1,
        flag2
    ) {
        if (!exactBackupFamily(
            method, url, timeout, headers, body, strings, flag1, flag2
        )) {
            return newHttp.call(
                this,
                method,
                url,
                timeout,
                headers,
                body,
                strings,
                flag1,
                flag2
            );
        }

        try {
            const klass = this.getClass();
            const nextField = field(klass, 'mNextRequestHandle');
            const mapField = field(klass, 'mRequestHandles');
            const glField = field(klass, 'mGLView');

            const requestId = nextField.getInt(this);
            nextField.setInt(this, requestId + 1);

            const parsedUrl = URL.$new(url);
            const request = Request.$new(
                requestId,
                method,
                parsedUrl,
                timeout,
                headers,
                body,
                strings
            );

            const requestMap = Java.cast(mapField.get(this), JavaMap);
            requestMap.put(IntegerClass.valueOf(requestId), request);

            const glView = glField.get(this);
            glView.queueEvent(ReplayRunnable.$new(requestId, url));

            log('local_request', {
                request_id: requestId,
                method: 'GET',
                family: 'nyanko-backups.ponosgames.com/',
                response_status: 0,
                response_header_shape: 'empty-object',
                response_body: 'null',
                response_flag: true
            });
            return requestId;
        } catch (error) {
            log('local_replay_error_fallback', { error: safeString(error) });
            return newHttp.call(
                this,
                method,
                url,
                timeout,
                headers,
                body,
                strings,
                flag1,
                flag2
            );
        }
    };

    log('replay_ready', {
        package: 'jp.kn.trace.battlecats',
        target: 'backup-offline-fallback',
        unknown_requests: 'original-fall-through'
    });
});
