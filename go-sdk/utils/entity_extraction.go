package utils

import (
	"strings"
)

// EntityInfo contains the extracted entity and record ID from a path.
type EntityInfo struct {
	Entity   string
	RecordID string
}

// ExtractEntity extracts the entity name and record ID from a REST URL path.
// Example: /api/v1/orders/123 → EntityInfo{Entity: "order", RecordID: "123"}
func ExtractEntity(path string) EntityInfo {
	segments := cleanPath(path)
	if len(segments) == 0 {
		return EntityInfo{}
	}

	var entity string
	var recordID string

	// Walk through segments to find the primary entity and its ID
	for i := 0; i < len(segments); i++ {
		seg := segments[i]

		if isIDSegment(seg) {
			// This is an ID for the previous resource
			recordID = seg
		} else {
			// This is a resource name
			entity = singularize(seg)
			recordID = "" // Reset record ID for new entity
			// Check if next segment is an ID
			if i+1 < len(segments) && isIDSegment(segments[i+1]) {
				recordID = segments[i+1]
				i++ // Skip the ID segment
			}
		}
	}

	return EntityInfo{
		Entity:   entity,
		RecordID: recordID,
	}
}

// ExtractParentEntity extracts the parent entity and its ID from a nested path.
// Example: /api/workspaces/ws_123/members/usr_456 →
//
//	EntityInfo{Entity: "workspace", RecordID: "ws_123"}
func ExtractParentEntity(path string) EntityInfo {
	segments := cleanPath(path)
	if len(segments) < 3 {
		return EntityInfo{}
	}

	// Find the first resource/ID pair
	for i := 0; i < len(segments)-2; i++ {
		if !isIDSegment(segments[i]) && isIDSegment(segments[i+1]) {
			return EntityInfo{
				Entity:   singularize(segments[i]),
				RecordID: segments[i+1],
			}
		}
	}

	return EntityInfo{}
}

// ExtractAllEntities extracts all entity/ID pairs from a nested path.
// Example: /api/workspaces/ws_123/projects/proj_456/members →
//
//	[]EntityInfo{
//	  {Entity: "workspace", RecordID: "ws_123"},
//	  {Entity: "project", RecordID: "proj_456"},
//	  {Entity: "member", RecordID: ""},
//	}
func ExtractAllEntities(path string) []EntityInfo {
	segments := cleanPath(path)
	if len(segments) == 0 {
		return nil
	}

	var entities []EntityInfo
	i := 0

	for i < len(segments) {
		seg := segments[i]

		if isIDSegment(seg) {
			// Orphan ID without a resource - skip
			i++
			continue
		}

		info := EntityInfo{
			Entity: singularize(seg),
		}

		// Check if next segment is an ID
		if i+1 < len(segments) && isIDSegment(segments[i+1]) {
			info.RecordID = segments[i+1]
			i += 2
		} else {
			i++
		}

		entities = append(entities, info)
	}

	return entities
}

// ExtractEntityFromPattern extracts entity info when the path contains placeholders.
// Example: /api/users/{user_id}/posts/{post_id} with actual path /api/users/123/posts/456
func ExtractEntityFromPattern(pattern, actualPath string) EntityInfo {
	patternSegs := cleanPath(pattern)
	actualSegs := cleanPath(actualPath)

	if len(patternSegs) != len(actualSegs) {
		return ExtractEntity(actualPath)
	}

	var entity string
	var recordID string

	for i := 0; i < len(patternSegs); i++ {
		patSeg := patternSegs[i]
		actSeg := actualSegs[i]

		if placeholderPattern.MatchString(patSeg) {
			// This is a placeholder, the actual value is the ID
			recordID = actSeg
		} else {
			// This is a resource name
			entity = singularize(patSeg)
			recordID = ""
			// Check if next segment is a placeholder
			if i+1 < len(patternSegs) && placeholderPattern.MatchString(patternSegs[i+1]) {
				recordID = actualSegs[i+1]
				i++
			}
		}
	}

	return EntityInfo{
		Entity:   entity,
		RecordID: recordID,
	}
}

// NormalizeEntityName normalizes an entity name to a consistent format.
func NormalizeEntityName(name string) string {
	name = strings.ToLower(name)
	name = strings.ReplaceAll(name, "-", "_")
	name = strings.ReplaceAll(name, " ", "_")
	return singularize(name)
}
