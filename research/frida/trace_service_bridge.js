'use strict';

/*
 * Research-only trace for the exact JP 15.7.1 MyActivity service bridge.
 *
 * This script must never ship in a product APK. It observes method calls and
 * calls the original implementation unchanged.
 */

Java.perform(function () {
    const CLASS_NAME = 'jp.co.ponos.battlecats.MyActivity';
    const MyActivity = Java.use(CLASS_NAME);

    function safeString(value) {
        try {
            if (value === null || value === undefined) return null;
            return String(value);
        } catch (_) {
            return '<unprintable>';
        }
    }

    function redactUrl(value) {
        const text = safeString(value);
        if (text === null) return null;
        const hash = text.indexOf('#');
        const noFragment = hash >= 0 ? text.slice(0, hash) : text;
        const q = noFragment.indexOf('?');
        return q >= 0 ? noFragment.slice(0, q) + '?<redacted>' : noFragment;
    }

    function javaClassName(value) {
        try {
            if (value === null || value === undefined) return null;
            return value.getClass().getName().toString();
        } catch (_) {
            return null;
        }
    }

    function summarize(value, declaredType) {
        if (value === null || value === undefined) return null;

        const type = declaredType || javaClassName(value) || typeof value;
        try {
            if (type === 'java.lang.String') {
                return { type: type, value: safeString(value) };
            }
            if (type === 'java.nio.ByteBuffer') {
                return {
                    type: type,
                    remaining: value.remaining(),
                    capacity: value.capacity()
                };
            }
            if (type === 'java.util.HashMap' || type === 'java.util.Map') {
                const keys = [];
                const iterator = value.keySet().iterator();
                while (iterator.hasNext() && keys.length < 32) {
                    keys.push(safeString(iterator.next()));
                }
                return { type: type, size: value.size(), keys: keys };
            }
            if (type.indexOf('[Ljava.lang.String;') >= 0) {
                return { type: type, length: value.length };
            }
            if (type === 'boolean' || type === 'int' || type === 'long'
                    || type === 'float' || type === 'double') {
                return { type: type, value: value };
            }
        } catch (error) {
            return { type: type, error: safeString(error) };
        }
        return { type: type };
    }

    function emit(payload) {
        payload.source = 'kneekura-jp15.7.1-service-trace';
        payload.ts_ms = Date.now();
        send(payload);
    }

    function describeOverloads(name) {
        let method;
        try {
            method = MyActivity[name];
        } catch (_) {
            return;
        }
        if (!method || !method.overloads) return;
        const rows = [];
        method.overloads.forEach(function (overload, index) {
            rows.push({
                index: index,
                arguments: overload.argumentTypes.map(function (t) { return t.className; }),
                returnType: overload.returnType.className
            });
        });
        emit({ kind: 'method_catalog', method: name, overloads: rows });
    }

    function hookGeneric(name, options) {
        let method;
        try {
            method = MyActivity[name];
        } catch (_) {
            emit({ kind: 'missing_method', method: name });
            return;
        }
        if (!method || !method.overloads) {
            emit({ kind: 'missing_method', method: name });
            return;
        }

        method.overloads.forEach(function (overload, index) {
            const argTypes = overload.argumentTypes.map(function (t) {
                return t.className;
            });

            overload.implementation = function () {
                const args = [];
                for (let i = 0; i < arguments.length; i++) {
                    if (options && options.urlArg === i) {
                        args.push({ type: argTypes[i], value: redactUrl(arguments[i]) });
                    } else {
                        args.push(summarize(arguments[i], argTypes[i]));
                    }
                }

                emit({
                    kind: 'call_enter',
                    method: name,
                    overload: index,
                    args: args
                });

                let result;
                try {
                    result = overload.call(this, ...arguments);
                } catch (error) {
                    emit({
                        kind: 'call_throw',
                        method: name,
                        overload: index,
                        error: safeString(error)
                    });
                    throw error;
                }

                emit({
                    kind: 'call_return',
                    method: name,
                    overload: index,
                    result: summarize(result, overload.returnType.className)
                });
                return result;
            };
        });
    }

    [
        'newHttpRequest',
        'isNetworkAvailable',
        'newResponse',
        'onResponseCodeHeaders',
        'onResponseData',
        'onResponseFinish'
    ].forEach(describeOverloads);

    hookGeneric('newHttpRequest', { urlArg: 0 });
    hookGeneric('isNetworkAvailable', {});
    hookGeneric('newResponse', {});
    hookGeneric('onResponseCodeHeaders', {});
    hookGeneric('onResponseData', {});
    hookGeneric('onResponseFinish', {});

    emit({
        kind: 'trace_ready',
        className: CLASS_NAME,
        note: 'observation only; originals called unchanged'
    });
});
