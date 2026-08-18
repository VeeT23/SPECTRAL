#pragma once

#include <cstdint>
#include <cstddef>
#include <cstring>
#include <cmath>
#include <limits>
#include <vector>

struct SolutionPoint
{
    float x;
    float y;
    float distance;
    float angle;
    float sweep;
};

struct SolutionSpan
{
    float start_distance;
    float end_distance;
    float percent_velocity; // Decoded directly from span payload speed field.
};

constexpr uint32_t kSolutionMagic = 0x314E4C53u; // "SLN1" in little-endian.
constexpr uint32_t kSolutionSpanMagic = 0x31534C53u; // "SLS1" in little-endian.
constexpr uint32_t kSolutionVersion = 2u;
constexpr size_t kSolutionHeaderSize = 12u;
constexpr size_t kSolutionPointSize = sizeof(float) * 5u;
constexpr size_t kSolutionSpanSize = sizeof(float) * 3u;

enum class SolutionDeserializeError : uint8_t
{
    None = 0,
    NullData,
    DataTooShort,
    HeaderReadFailed,
    MagicMismatch,
    VersionMismatch,
    CountOverflow,
    LengthMismatch,
    ItemReadFailed
};

struct SolutionDeserializeDebugInfo
{
    SolutionDeserializeError error = SolutionDeserializeError::None;
    uint32_t actual_magic = 0u;
    uint32_t expected_magic = 0u;
    uint32_t actual_version = 0u;
    uint32_t expected_version = 0u;
    uint32_t element_count = 0u;
    size_t data_length = 0u;
    size_t expected_length = 0u;
    uint32_t failed_index = 0u;
};

inline void initSolutionDeserializeDebugInfo(SolutionDeserializeDebugInfo *debug_info)
{
    if (debug_info != nullptr)
    {
        *debug_info = SolutionDeserializeDebugInfo{};
    }
}

inline const char *solutionDeserializeErrorToString(SolutionDeserializeError error)
{
    switch (error)
    {
    case SolutionDeserializeError::None:
        return "None";
    case SolutionDeserializeError::NullData:
        return "Data pointer is null";
    case SolutionDeserializeError::DataTooShort:
        return "Data too short for header";
    case SolutionDeserializeError::HeaderReadFailed:
        return "Failed reading header";
    case SolutionDeserializeError::MagicMismatch:
        return "Magic mismatch";
    case SolutionDeserializeError::VersionMismatch:
        return "Version mismatch";
    case SolutionDeserializeError::CountOverflow:
        return "Element count overflow";
    case SolutionDeserializeError::LengthMismatch:
        return "Payload length mismatch";
    case SolutionDeserializeError::ItemReadFailed:
        return "Failed reading element data";
    default:
        return "Unknown deserialize error";
    }
}

inline bool read_u32_le(const uint8_t *data, size_t data_len, size_t offset, uint32_t &out)
{
    if (offset + sizeof(uint32_t) > data_len)
    {
        return false;
    }

    out = static_cast<uint32_t>(data[offset]) |
          (static_cast<uint32_t>(data[offset + 1]) << 8) |
          (static_cast<uint32_t>(data[offset + 2]) << 16) |
          (static_cast<uint32_t>(data[offset + 3]) << 24);
    return true;
}

inline bool read_f32_le(const uint8_t *data, size_t data_len, size_t offset, float &out)
{
    uint32_t raw = 0;
    if (!read_u32_le(data, data_len, offset, raw))
    {
        return false;
    }

    std::memcpy(&out, &raw, sizeof(float));
    return true;
}
static const uint8_t kSolutionData[] = {
    0x53, 0x4C, 0x4E, 0x31, 0x02, 0x00, 0x00, 0x00, 0x0D, 0x00, 0x00, 0x00, 0x87, 0x21, 0x1A, 0x3C,
    0xF5, 0x7A, 0x45, 0x3E, 0x00, 0x00, 0x00, 0x00, 0x58, 0x4E, 0xFB, 0xC0, 0x00, 0x00, 0xA0, 0x41,
    0xB1, 0xB3, 0x11, 0x40, 0xAC, 0x27, 0xDB, 0x3E, 0xC6, 0x28, 0x18, 0x40, 0xDD, 0xF5, 0xA6, 0x42,
    0x00, 0x00, 0xA0, 0x41, 0xE8, 0x16, 0x0E, 0x40, 0x59, 0xB6, 0x14, 0x40, 0x8A, 0xBC, 0x89, 0x40,
    0xA0, 0x78, 0x27, 0x43, 0x00, 0x00, 0xA0, 0x41, 0xFB, 0x99, 0xAE, 0x3F, 0x51, 0x61, 0x0B, 0x40,
    0x9D, 0x04, 0xA8, 0x40, 0x00, 0x00, 0xB4, 0xC2, 0x00, 0x00, 0xA0, 0x41, 0xFB, 0x2C, 0xE1, 0x3F,
    0x35, 0x69, 0xEB, 0x3F, 0xF6, 0xCC, 0xBA, 0x40, 0xF6, 0x6D, 0xBB, 0xC1, 0x00, 0x00, 0xA0, 0x41,
    0x24, 0xF6, 0x05, 0x40, 0x4D, 0x78, 0xC2, 0x3F, 0x7F, 0x5D, 0xCA, 0x40, 0xFE, 0xBF, 0xA5, 0xC2,
    0x00, 0x00, 0xA0, 0x41, 0x6F, 0xA5, 0xF5, 0x3F, 0x93, 0xF2, 0x1E, 0x3F, 0xE2, 0x83, 0xEA, 0x40,
    0xE9, 0xA8, 0x2D, 0xC3, 0x00, 0x00, 0xA0, 0x41, 0x50, 0xBE, 0x9D, 0x3F, 0x75, 0x31, 0x2C, 0x3F,
    0xD5, 0x58, 0x00, 0x41, 0x00, 0x00, 0x07, 0x43, 0x00, 0x00, 0xA0, 0x41, 0xCA, 0x55, 0x9B, 0x3F,
    0x99, 0x11, 0x88, 0x3F, 0x87, 0x82, 0x07, 0x41, 0xF7, 0x08, 0xBD, 0x41, 0x00, 0x00, 0xA0, 0x41,
    0x47, 0x59, 0xD9, 0x3F, 0x3B, 0xF5, 0xA1, 0x3F, 0xEE, 0x32, 0x10, 0x41, 0x00, 0x00, 0xB4, 0x42,
    0x00, 0x00, 0xA0, 0x41, 0x10, 0x63, 0xAA, 0x3F, 0xFE, 0x72, 0xBC, 0x3F, 0x4B, 0x32, 0x18, 0x41,
    0x47, 0x09, 0x15, 0xC3, 0x00, 0x00, 0xA0, 0x41, 0x32, 0x90, 0x5D, 0x3F, 0xFE, 0x72, 0xBC, 0x3F,
    0xA7, 0x35, 0x22, 0x41, 0x00, 0x00, 0xB4, 0x42, 0x00, 0x00, 0xA0, 0x41, 0x87, 0x47, 0x7F, 0x3E,
    0x8D, 0x40, 0x03, 0x40, 0xBD, 0xFF, 0x4F, 0x41, 0x00, 0x00, 0xB4, 0xC2, 0x00, 0x00, 0xA0, 0x41
};
static const size_t kSolutionDataLength = sizeof(kSolutionData);

static const uint8_t kSolutionSpanData[] = {
    0x53, 0x4C, 0x53, 0x31, 0x02, 0x00, 0x00, 0x00, 0x09, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x66, 0x66, 0xE6, 0x3F, 0x00, 0x00, 0x80, 0x3F, 0x66, 0x66, 0xE6, 0x3F, 0xC6, 0x28, 0x18, 0x40,
    0x9A, 0x99, 0x99, 0x3E, 0xC6, 0x28, 0x18, 0x40, 0x33, 0x33, 0x73, 0x40, 0x00, 0x00, 0x80, 0x3F,
    0x33, 0x33, 0x73, 0x40, 0x0C, 0x83, 0x8C, 0x40, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x83, 0x8C, 0x40,
    0x2F, 0xED, 0xDF, 0x40, 0xCD, 0xCC, 0xCC, 0x3E, 0x2F, 0xED, 0xDF, 0x40, 0xC8, 0x77, 0xE8, 0x40,
    0xCD, 0xCC, 0x4C, 0x3E, 0xC8, 0x77, 0xE8, 0x40, 0x3F, 0x31, 0x17, 0x41, 0xCD, 0xCC, 0xCC, 0x3E,
    0x3F, 0x31, 0x17, 0x41, 0x54, 0xBA, 0x44, 0x41, 0x00, 0x00, 0x00, 0x00, 0x54, 0xBA, 0x44, 0x41,
    0x52, 0xD8, 0x8C, 0x41, 0xCD, 0xCC, 0xCC, 0x3E
};
static const size_t kSolutionSpanDataLength = sizeof(kSolutionSpanData);
inline bool deserializeSolutionSpans(
    const uint8_t *data,
    size_t data_len,
    std::vector<SolutionSpan> &out_spans,
    SolutionDeserializeDebugInfo *debug_info = nullptr)
{
    out_spans.clear();
    initSolutionDeserializeDebugInfo(debug_info);

    if (debug_info != nullptr)
    {
        debug_info->expected_magic = kSolutionSpanMagic;
        debug_info->expected_version = kSolutionVersion;
        debug_info->data_length = data_len;
    }

    if (data == nullptr)
    {
        if (debug_info != nullptr)
        {
            debug_info->error = SolutionDeserializeError::NullData;
            debug_info->expected_length = kSolutionHeaderSize;
        }
        return false;
    }

    if (data_len < kSolutionHeaderSize)
    {
        if (debug_info != nullptr)
        {
            debug_info->error = SolutionDeserializeError::DataTooShort;
            debug_info->expected_length = kSolutionHeaderSize;
        }
        return false;
    }

    uint32_t magic = 0;
    uint32_t version = 0;
    uint32_t span_count = 0;

    if (!read_u32_le(data, data_len, 0, magic) ||
        !read_u32_le(data, data_len, 4, version) ||
        !read_u32_le(data, data_len, 8, span_count))
    {
        if (debug_info != nullptr)
        {
            debug_info->error = SolutionDeserializeError::HeaderReadFailed;
        }
        return false;
    }

    if (debug_info != nullptr)
    {
        debug_info->actual_magic = magic;
        debug_info->actual_version = version;
        debug_info->element_count = span_count;
    }

    if (magic != kSolutionSpanMagic)
    {
        if (debug_info != nullptr)
        {
            debug_info->error = SolutionDeserializeError::MagicMismatch;
        }
        return false;
    }

    if (version != kSolutionVersion)
    {
        if (debug_info != nullptr)
        {
            debug_info->error = SolutionDeserializeError::VersionMismatch;
        }
        return false;
    }

    const size_t max_count = (std::numeric_limits<size_t>::max() - kSolutionHeaderSize) / kSolutionSpanSize;
    if (static_cast<size_t>(span_count) > max_count)
    {
        if (debug_info != nullptr)
        {
            debug_info->error = SolutionDeserializeError::CountOverflow;
        }
        return false;
    }

    const size_t expected_length = kSolutionHeaderSize + static_cast<size_t>(span_count) * kSolutionSpanSize;
    if (debug_info != nullptr)
    {
        debug_info->expected_length = expected_length;
    }

    if (expected_length != data_len)
    {
        if (debug_info != nullptr)
        {
            debug_info->error = SolutionDeserializeError::LengthMismatch;
        }
        return false;
    }

    out_spans.reserve(span_count);
    size_t offset = kSolutionHeaderSize;

    for (uint32_t i = 0; i < span_count; ++i)
    {
        SolutionSpan span{};
        if (!read_f32_le(data, data_len, offset + 0, span.start_distance) ||
            !read_f32_le(data, data_len, offset + 4, span.end_distance) ||
            !read_f32_le(data, data_len, offset + 8, span.percent_velocity))
        {
            out_spans.clear();
            if (debug_info != nullptr)
            {
                debug_info->error = SolutionDeserializeError::ItemReadFailed;
                debug_info->failed_index = i;
            }
            return false;
        }

        if (span.percent_velocity < 0.0f)
        {
            span.percent_velocity = 0.0f;
        }
        else if (span.percent_velocity > 1.0f)
        {
            span.percent_velocity = 1.0f;
        }

        out_spans.push_back(span);
        offset += kSolutionSpanSize;
    }

    return true;
}

inline std::vector<SolutionSpan> deserializeSolutionSpans(const uint8_t *data, size_t data_len)
{
    std::vector<SolutionSpan> spans;
    deserializeSolutionSpans(data, data_len, spans, nullptr);
    return spans;
}

inline bool deserializeEmbeddedSolutionSpans(
    std::vector<SolutionSpan> &out_spans,
    SolutionDeserializeDebugInfo *debug_info = nullptr)
{
    return deserializeSolutionSpans(kSolutionSpanData, kSolutionSpanDataLength, out_spans, debug_info);
}

inline std::vector<SolutionSpan> deserializeEmbeddedSolutionSpans()
{
    return deserializeSolutionSpans(kSolutionSpanData, kSolutionSpanDataLength);
}


inline bool deserializeSolutionPoints(
    const uint8_t *data,
    size_t data_len,
    std::vector<SolutionPoint> &out_points,
    SolutionDeserializeDebugInfo *debug_info = nullptr)
{
    out_points.clear();
    initSolutionDeserializeDebugInfo(debug_info);

    if (debug_info != nullptr)
    {
        debug_info->expected_magic = kSolutionMagic;
        debug_info->expected_version = kSolutionVersion;
        debug_info->data_length = data_len;
    }

    if (data == nullptr)
    {
        if (debug_info != nullptr)
        {
            debug_info->error = SolutionDeserializeError::NullData;
            debug_info->expected_length = kSolutionHeaderSize;
        }
        return false;
    }

    if (data_len < kSolutionHeaderSize)
    {
        if (debug_info != nullptr)
        {
            debug_info->error = SolutionDeserializeError::DataTooShort;
            debug_info->expected_length = kSolutionHeaderSize;
        }
        return false;
    }

    uint32_t magic = 0;
    uint32_t version = 0;
    uint32_t point_count = 0;

    if (!read_u32_le(data, data_len, 0, magic) ||
        !read_u32_le(data, data_len, 4, version) ||
        !read_u32_le(data, data_len, 8, point_count))
    {
        if (debug_info != nullptr)
        {
            debug_info->error = SolutionDeserializeError::HeaderReadFailed;
        }
        return false;
    }

    if (debug_info != nullptr)
    {
        debug_info->actual_magic = magic;
        debug_info->actual_version = version;
        debug_info->element_count = point_count;
    }

    if (magic != kSolutionMagic)
    {
        if (debug_info != nullptr)
        {
            debug_info->error = SolutionDeserializeError::MagicMismatch;
        }
        return false;
    }

    if (version != kSolutionVersion)
    {
        if (debug_info != nullptr)
        {
            debug_info->error = SolutionDeserializeError::VersionMismatch;
        }
        return false;
    }

    const size_t max_count = (std::numeric_limits<size_t>::max() - kSolutionHeaderSize) / kSolutionPointSize;
    if (static_cast<size_t>(point_count) > max_count)
    {
        if (debug_info != nullptr)
        {
            debug_info->error = SolutionDeserializeError::CountOverflow;
        }
        return false;
    }

    const size_t expected_length = kSolutionHeaderSize + static_cast<size_t>(point_count) * kSolutionPointSize;
    if (debug_info != nullptr)
    {
        debug_info->expected_length = expected_length;
    }

    if (expected_length != data_len)
    {
        if (debug_info != nullptr)
        {
            debug_info->error = SolutionDeserializeError::LengthMismatch;
        }
        return false;
    }

    out_points.reserve(point_count);
    size_t offset = kSolutionHeaderSize;

    for (uint32_t i = 0; i < point_count; ++i)
    {
        SolutionPoint point{};
        if (!read_f32_le(data, data_len, offset + 0, point.x) ||
            !read_f32_le(data, data_len, offset + 4, point.y) ||
            !read_f32_le(data, data_len, offset + 8, point.distance) ||
            !read_f32_le(data, data_len, offset + 12, point.angle) ||
            !read_f32_le(data, data_len, offset + 16, point.sweep))
        {
            out_points.clear();
            if (debug_info != nullptr)
            {
                debug_info->error = SolutionDeserializeError::ItemReadFailed;
                debug_info->failed_index = i;
            }
            return false;
        }

        out_points.push_back(point);
        offset += kSolutionPointSize;
    }

    return true;
}

inline std::vector<SolutionPoint> deserializeSolutionPoints(const uint8_t *data, size_t data_len)
{
    std::vector<SolutionPoint> points;
    deserializeSolutionPoints(data, data_len, points, nullptr);
    return points;
}

inline bool deserializeEmbeddedSolutionPoints(
    std::vector<SolutionPoint> &out_points,
    SolutionDeserializeDebugInfo *debug_info = nullptr)
{
    return deserializeSolutionPoints(kSolutionData, kSolutionDataLength, out_points, debug_info);
}

inline std::vector<SolutionPoint> deserializeEmbeddedSolutionPoints()
{
    return deserializeSolutionPoints(kSolutionData, kSolutionDataLength);
}

