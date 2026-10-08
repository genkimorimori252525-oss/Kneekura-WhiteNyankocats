#include "kneekura_shim.h"

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#define KNEEKURA_SIDECAR_SIZE 64u
#define KNEEKURA_SIDECAR_PAYLOAD_OFFSET 24u
#define KNEEKURA_SIDECAR_PAYLOAD_SIZE 40u

static const uint8_t kSidecarMagic[8] = {
        'K', 'N', 'Y', 'S', 'C', 'A', 'R', '1'
};

static void write_u32_le(uint8_t *out, uint32_t value) {
    out[0] = (uint8_t) (value & 0xffu);
    out[1] = (uint8_t) ((value >> 8) & 0xffu);
    out[2] = (uint8_t) ((value >> 16) & 0xffu);
    out[3] = (uint8_t) ((value >> 24) & 0xffu);
}

static uint32_t read_u32_le(const uint8_t *in) {
    return ((uint32_t) in[0])
            | ((uint32_t) in[1] << 8)
            | ((uint32_t) in[2] << 16)
            | ((uint32_t) in[3] << 24);
}

static void write_u64_le(uint8_t *out, uint64_t value) {
    for (uint32_t index = 0; index < 8u; ++index) {
        out[index] = (uint8_t) ((value >> (index * 8u)) & 0xffu);
    }
}

static uint64_t read_u64_le(const uint8_t *in) {
    uint64_t value = 0u;
    for (uint32_t index = 0; index < 8u; ++index) {
        value |= ((uint64_t) in[index]) << (index * 8u);
    }
    return value;
}

static uint32_t crc32_bytes(const uint8_t *data, size_t size) {
    uint32_t crc = 0xffffffffu;
    for (size_t index = 0; index < size; ++index) {
        crc ^= (uint32_t) data[index];
        for (uint32_t bit = 0; bit < 8u; ++bit) {
            uint32_t mask = (uint32_t) (-(int32_t) (crc & 1u));
            crc = (crc >> 1) ^ (0xedb88320u & mask);
        }
    }
    return ~crc;
}

uint32_t kneekura_profile_mode_valid(uint32_t profile_mode) {
    return profile_mode == (uint32_t) KNEEKURA_PROFILE_PERSONAL_MAX
            || profile_mode == (uint32_t) KNEEKURA_PROFILE_PRACTICE_CLEAN;
}

int32_t kneekura_sidecar_state_init(
        uint32_t profile_mode,
        KneekuraSidecarState *state) {
    if (state == NULL || kneekura_profile_mode_valid(profile_mode) == 0u) {
        return KNEEKURA_STATUS_INVALID_ARGUMENT;
    }

    memset(state, 0, sizeof(*state));
    state->schema_version = KNEEKURA_SIDECAR_SCHEMA_VERSION;
    state->profile_mode = profile_mode;
    state->last_seen_epoch_day = KNEEKURA_LOGIN_DAY_UNSET;
    state->last_claim_epoch_day = KNEEKURA_LOGIN_DAY_UNSET;
    return KNEEKURA_STATUS_OK;
}

int32_t kneekura_clock_observe_epoch_day(
        KneekuraSidecarState *state,
        int64_t observed_epoch_day) {
    if (state == NULL
            || state->schema_version != KNEEKURA_SIDECAR_SCHEMA_VERSION
            || kneekura_profile_mode_valid(state->profile_mode) == 0u) {
        return KNEEKURA_STATUS_INVALID_ARGUMENT;
    }

    if (state->last_seen_epoch_day == KNEEKURA_LOGIN_DAY_UNSET
            || observed_epoch_day > state->last_seen_epoch_day) {
        state->last_seen_epoch_day = observed_epoch_day;
    }

    return kneekura_login_claim_available(state);
}

int32_t kneekura_login_claim_available(
        const KneekuraSidecarState *state) {
    if (state == NULL
            || state->schema_version != KNEEKURA_SIDECAR_SCHEMA_VERSION
            || kneekura_profile_mode_valid(state->profile_mode) == 0u) {
        return KNEEKURA_STATUS_INVALID_ARGUMENT;
    }
    if (state->last_seen_epoch_day == KNEEKURA_LOGIN_DAY_UNSET) {
        return 0;
    }
    return state->last_seen_epoch_day > state->last_claim_epoch_day ? 1 : 0;
}

int32_t kneekura_login_claim(
        KneekuraSidecarState *state,
        uint32_t cycle_length,
        uint32_t *claimed_index) {
    if (state == NULL || cycle_length == 0u
            || state->schema_version != KNEEKURA_SIDECAR_SCHEMA_VERSION
            || kneekura_profile_mode_valid(state->profile_mode) == 0u) {
        return KNEEKURA_STATUS_INVALID_ARGUMENT;
    }

    int32_t available = kneekura_login_claim_available(state);
    if (available <= 0) {
        return available;
    }

    uint32_t current = state->login_cycle_index % cycle_length;
    if (claimed_index != NULL) {
        *claimed_index = current;
    }
    state->login_cycle_index = (current + 1u) % cycle_length;
    state->last_claim_epoch_day = state->last_seen_epoch_day;
    return 1;
}

size_t kneekura_sidecar_encoded_size(void) {
    return KNEEKURA_SIDECAR_SIZE;
}

int32_t kneekura_sidecar_encode(
        const KneekuraSidecarState *state,
        uint8_t *output,
        size_t output_size) {
    if (state == NULL || output == NULL || output_size < KNEEKURA_SIDECAR_SIZE
            || state->schema_version != KNEEKURA_SIDECAR_SCHEMA_VERSION
            || kneekura_profile_mode_valid(state->profile_mode) == 0u) {
        return KNEEKURA_STATUS_INVALID_ARGUMENT;
    }

    memset(output, 0, KNEEKURA_SIDECAR_SIZE);
    memcpy(output, kSidecarMagic, sizeof(kSidecarMagic));
    write_u32_le(output + 8u, KNEEKURA_SIDECAR_SCHEMA_VERSION);
    write_u32_le(output + 12u, KNEEKURA_SIDECAR_PAYLOAD_SIZE);

    write_u32_le(output + 24u, state->profile_mode);
    write_u32_le(output + 28u, state->login_cycle_index);
    write_u64_le(output + 32u, (uint64_t) state->last_seen_epoch_day);
    write_u64_le(output + 40u, (uint64_t) state->last_claim_epoch_day);
    write_u32_le(output + 48u, state->event_snapshot_version);
    write_u32_le(output + 52u, state->gacha_config_version);
    write_u64_le(output + 56u, state->extension_flags);

    uint32_t checksum = crc32_bytes(
            output + KNEEKURA_SIDECAR_PAYLOAD_OFFSET,
            KNEEKURA_SIDECAR_PAYLOAD_SIZE);
    write_u32_le(output + 16u, checksum);
    return KNEEKURA_STATUS_OK;
}

int32_t kneekura_sidecar_decode(
        const uint8_t *input,
        size_t input_size,
        KneekuraSidecarState *state) {
    if (input == NULL || state == NULL || input_size != KNEEKURA_SIDECAR_SIZE) {
        return KNEEKURA_STATUS_INVALID_ARGUMENT;
    }
    if (memcmp(input, kSidecarMagic, sizeof(kSidecarMagic)) != 0) {
        return KNEEKURA_STATUS_BAD_MAGIC;
    }

    uint32_t schema = read_u32_le(input + 8u);
    uint32_t payload_size = read_u32_le(input + 12u);
    if (schema != KNEEKURA_SIDECAR_SCHEMA_VERSION
            || payload_size != KNEEKURA_SIDECAR_PAYLOAD_SIZE) {
        return KNEEKURA_STATUS_UNSUPPORTED_SCHEMA;
    }

    uint32_t expected_checksum = read_u32_le(input + 16u);
    uint32_t actual_checksum = crc32_bytes(
            input + KNEEKURA_SIDECAR_PAYLOAD_OFFSET,
            KNEEKURA_SIDECAR_PAYLOAD_SIZE);
    if (expected_checksum != actual_checksum) {
        return KNEEKURA_STATUS_CHECKSUM_MISMATCH;
    }

    KneekuraSidecarState decoded;
    memset(&decoded, 0, sizeof(decoded));
    decoded.schema_version = schema;
    decoded.profile_mode = read_u32_le(input + 24u);
    decoded.login_cycle_index = read_u32_le(input + 28u);
    decoded.last_seen_epoch_day = (int64_t) read_u64_le(input + 32u);
    decoded.last_claim_epoch_day = (int64_t) read_u64_le(input + 40u);
    decoded.event_snapshot_version = read_u32_le(input + 48u);
    decoded.gacha_config_version = read_u32_le(input + 52u);
    decoded.extension_flags = read_u64_le(input + 56u);

    if (kneekura_profile_mode_valid(decoded.profile_mode) == 0u) {
        return KNEEKURA_STATUS_INVALID_ARGUMENT;
    }
    *state = decoded;
    return KNEEKURA_STATUS_OK;
}

static int32_t write_all(int fd, const uint8_t *data, size_t size) {
    size_t written = 0u;
    while (written < size) {
        ssize_t result = write(fd, data + written, size - written);
        if (result < 0) {
            if (errno == EINTR) {
                continue;
            }
            return KNEEKURA_STATUS_IO_ERROR;
        }
        if (result == 0) {
            return KNEEKURA_STATUS_IO_ERROR;
        }
        written += (size_t) result;
    }
    return KNEEKURA_STATUS_OK;
}

static int32_t read_exact_file(const char *path, uint8_t *buffer, size_t size) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        return errno == ENOENT ? KNEEKURA_STATUS_NOT_FOUND : KNEEKURA_STATUS_IO_ERROR;
    }

    size_t used = 0u;
    int32_t status = KNEEKURA_STATUS_OK;
    while (used < size) {
        ssize_t result = read(fd, buffer + used, size - used);
        if (result < 0) {
            if (errno == EINTR) {
                continue;
            }
            status = KNEEKURA_STATUS_IO_ERROR;
            break;
        }
        if (result == 0) {
            status = KNEEKURA_STATUS_IO_ERROR;
            break;
        }
        used += (size_t) result;
    }

    if (status == KNEEKURA_STATUS_OK) {
        uint8_t extra = 0u;
        ssize_t extra_read = read(fd, &extra, 1u);
        if (extra_read != 0) {
            status = KNEEKURA_STATUS_IO_ERROR;
        }
    }
    if (close(fd) != 0 && status == KNEEKURA_STATUS_OK) {
        status = KNEEKURA_STATUS_IO_ERROR;
    }
    return status;
}

static int make_suffix_path(
        const char *path,
        const char *suffix,
        char *output,
        size_t output_size) {
    int count = snprintf(output, output_size, "%s%s", path, suffix);
    return count > 0 && (size_t) count < output_size;
}

static void sync_parent_directory(const char *path) {
    char directory[1024];
    size_t length = strlen(path);
    if (length == 0u || length >= sizeof(directory)) {
        return;
    }
    memcpy(directory, path, length + 1u);

    char *slash = strrchr(directory, '/');
    if (slash == NULL) {
        strcpy(directory, ".");
    } else if (slash == directory) {
        slash[1] = '\0';
    } else {
        *slash = '\0';
    }

#ifdef O_DIRECTORY
    int fd = open(directory, O_RDONLY | O_DIRECTORY);
#else
    int fd = open(directory, O_RDONLY);
#endif
    if (fd >= 0) {
        (void) fsync(fd);
        (void) close(fd);
    }
}

int32_t kneekura_sidecar_save_atomic(
        const char *path,
        const KneekuraSidecarState *state) {
    if (kneekura_feature_enabled(KNEEKURA_FEATURE_LOCAL_STATE) == 0u) {
        return KNEEKURA_STATUS_DISABLED;
    }
    if (path == NULL || path[0] == '\0' || state == NULL) {
        return KNEEKURA_STATUS_INVALID_ARGUMENT;
    }

    uint8_t encoded[KNEEKURA_SIDECAR_SIZE];
    int32_t status = kneekura_sidecar_encode(state, encoded, sizeof(encoded));
    if (status != KNEEKURA_STATUS_OK) {
        return status;
    }

    char temp_path[1024];
    char backup_path[1024];
    if (!make_suffix_path(path, ".tmp", temp_path, sizeof(temp_path))
            || !make_suffix_path(path, ".bak", backup_path, sizeof(backup_path))) {
        return KNEEKURA_STATUS_INVALID_ARGUMENT;
    }

    int fd = open(temp_path, O_WRONLY | O_CREAT | O_TRUNC, 0600);
    if (fd < 0) {
        return KNEEKURA_STATUS_IO_ERROR;
    }
    status = write_all(fd, encoded, sizeof(encoded));
    if (status == KNEEKURA_STATUS_OK && fsync(fd) != 0) {
        status = KNEEKURA_STATUS_IO_ERROR;
    }
    if (close(fd) != 0 && status == KNEEKURA_STATUS_OK) {
        status = KNEEKURA_STATUS_IO_ERROR;
    }
    if (status != KNEEKURA_STATUS_OK) {
        (void) unlink(temp_path);
        return status;
    }

    struct stat existing;
    int had_primary = stat(path, &existing) == 0;
    if (had_primary) {
        (void) unlink(backup_path);
        if (rename(path, backup_path) != 0) {
            (void) unlink(temp_path);
            return KNEEKURA_STATUS_IO_ERROR;
        }
    }

    if (rename(temp_path, path) != 0) {
        if (had_primary) {
            (void) rename(backup_path, path);
        }
        (void) unlink(temp_path);
        return KNEEKURA_STATUS_IO_ERROR;
    }

    sync_parent_directory(path);
    return KNEEKURA_STATUS_OK;
}

int32_t kneekura_sidecar_load(
        const char *path,
        KneekuraSidecarState *state) {
    if (kneekura_feature_enabled(KNEEKURA_FEATURE_LOCAL_STATE) == 0u) {
        return KNEEKURA_STATUS_DISABLED;
    }
    if (path == NULL || path[0] == '\0' || state == NULL) {
        return KNEEKURA_STATUS_INVALID_ARGUMENT;
    }

    uint8_t encoded[KNEEKURA_SIDECAR_SIZE];
    int32_t status = read_exact_file(path, encoded, sizeof(encoded));
    if (status == KNEEKURA_STATUS_OK) {
        status = kneekura_sidecar_decode(encoded, sizeof(encoded), state);
        if (status == KNEEKURA_STATUS_OK) {
            return status;
        }
    }

    char backup_path[1024];
    if (!make_suffix_path(path, ".bak", backup_path, sizeof(backup_path))) {
        return status;
    }
    int32_t backup_status = read_exact_file(
            backup_path, encoded, sizeof(encoded));
    if (backup_status != KNEEKURA_STATUS_OK) {
        return status;
    }
    return kneekura_sidecar_decode(encoded, sizeof(encoded), state);
}