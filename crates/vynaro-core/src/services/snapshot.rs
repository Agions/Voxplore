//! vynaro-core · SnapshotService 工程版本历史与快照服务

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tokio::sync::Mutex;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectSnapshot {
    pub id: String,
    pub project_id: String,
    pub version_tag: String,
    pub kind: String, // "auto" | "manual"
    pub name: String,
    pub created_at: DateTime<Utc>,
    pub project_json: String,
}

#[derive(Debug, Default)]
pub struct SnapshotService {
    // 内存中的快照索引，Key 为 project_id
    index: Mutex<HashMap<String, Vec<ProjectSnapshot>>>,
}

impl SnapshotService {
    pub fn new() -> Self {
        Self::default()
    }

    /// 获取指定工程的所有历史快照 (按时间从最新到最旧排序)
    pub async fn list_snapshots(&self, project_id: &str) -> Vec<ProjectSnapshot> {
        let index = self.index.lock().await;
        if let Some(list) = index.get(project_id) {
            let mut res = list.clone();
            res.sort_by(|a, b| b.created_at.cmp(&a.created_at));
            res
        } else {
            Vec::new()
        }
    }

    /// 创建一个新快照 (自动计算版本号如 v1.0, v1.1, 保留最多 30 个历史版本)
    pub async fn create_snapshot(
        &self,
        project_id: &str,
        name: &str,
        kind: &str,
        project_json: &str,
    ) -> ProjectSnapshot {
        let mut index = self.index.lock().await;
        let list = index.entry(project_id.to_string()).or_default();

        let count = list.len() + 1;
        let version_tag = format!("v1.{}", count - 1);
        let id = format!("snap_{}_{}", Utc::now().timestamp_millis(), count);

        let snapshot = ProjectSnapshot {
            id,
            project_id: project_id.to_string(),
            version_tag,
            kind: kind.to_string(),
            name: name.to_string(),
            created_at: Utc::now(),
            project_json: project_json.to_string(),
        };

        list.insert(0, snapshot.clone());
        list.truncate(30); // 最多保留 30 个版本

        snapshot
    }

    /// 恢复特定快照 (返回快照内保存的工程 JSON)
    pub async fn restore_snapshot(
        &self,
        project_id: &str,
        snapshot_id: &str,
    ) -> Option<ProjectSnapshot> {
        let list = self.list_snapshots(project_id).await;
        list.into_iter().find(|s| s.id == snapshot_id)
    }

    /// 删除特定快照
    pub async fn delete_snapshot(&self, project_id: &str, snapshot_id: &str) -> bool {
        let mut index = self.index.lock().await;
        if let Some(list) = index.get_mut(project_id) {
            let initial_len = list.len();
            list.retain(|s| s.id != snapshot_id);
            list.len() < initial_len
        } else {
            false
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_snapshot_lifecycle() {
        let svc = SnapshotService::new();
        let prj_id = "test_project_123";

        // 初始为空
        let list = svc.list_snapshots(prj_id).await;
        assert!(list.is_empty());

        // 创建两个快照
        let s1 = svc
            .create_snapshot(prj_id, "初始素材导入", "auto", "{\"name\":\"Project 1\"}")
            .await;
        let s2 = svc
            .create_snapshot(
                prj_id,
                "手动微调文案",
                "manual",
                "{\"name\":\"Project 1 - V2\"}",
            )
            .await;

        let list = svc.list_snapshots(prj_id).await;
        assert_eq!(list.len(), 2);
        assert_eq!(list[0].id, s2.id); // 最新在前

        // 恢复测试
        let restored = svc.restore_snapshot(prj_id, &s1.id).await;
        assert!(restored.is_some());
        assert_eq!(restored.unwrap().project_json, "{\"name\":\"Project 1\"}");

        // 删除测试
        let deleted = svc.delete_snapshot(prj_id, &s2.id).await;
        assert!(deleted);
        let list_after = svc.list_snapshots(prj_id).await;
        assert_eq!(list_after.len(), 1);
    }
}
