/**
 * Vynaro v1.0.1 · useSnapshot Hook
 *
 * 封装工程版本历史快照的拉取、创建、还原与删除
 */

import { useCallback } from "react";
import { toast } from "sonner";
import { projectIpc } from "../ipc/commands";
import type { Project, ProjectSnapshot } from "../ipc/types.gen";
import { useProjectStore } from "../stores/project-store";
import { useSnapshotStore } from "../stores/snapshot-store";

export function useSnapshot() {
  const { current, currentPath, setCurrentRecord } = useProjectStore();
  const {
    snapshots,
    setSnapshots,
    isDrawerOpen,
    openDrawer,
    closeDrawer,
    toggleDrawer,
  } = useSnapshotStore();

  const projectId = current?.id ?? "default_project";

  /** 加载全量历史快照 */
  const fetchSnapshots = useCallback(async () => {
    if (!projectId) return;
    try {
      const list = await projectIpc.snapshotList(projectId);
      setSnapshots(list);
    } catch (err) {
      console.warn("拉取快照失败:", err);
    }
  }, [projectId, setSnapshots]);

  /** 手动或自动捕获快照 */
  const createSnapshot = useCallback(
    async (name: string, kind: "auto" | "manual" = "manual") => {
      if (!current) {
        toast.error("未找到激活的解说工程");
        return null;
      }
      try {
        const jsonStr = JSON.stringify(current);
        const snap = await projectIpc.snapshotCreate(
          current.id,
          name,
          kind,
          jsonStr,
        );
        await fetchSnapshots();
        if (kind === "manual") {
          toast.success(`已创建版本快照: ${snap.versionTag} (${name})`);
        }
        return snap;
      } catch (err) {
        toast.error(`创建快照失败: ${String(err)}`);
        return null;
      }
    },
    [current, fetchSnapshots],
  );

  /** 还原特定快照 */
  const restoreSnapshot = useCallback(
    async (snapshotId: string) => {
      if (!current || !currentPath) {
        toast.error("无法还原: 未指定当前工程磁盘路径");
        return false;
      }
      try {
        // 先备份当前状态为临时安全快照
        await projectIpc.snapshotCreate(
          current.id,
          "还原前安全自动备份",
          "auto",
          JSON.stringify(current),
        );

        // 还原目标快照
        const snap = await projectIpc.snapshotRestore(current.id, snapshotId);
        const restoredProject: Project = JSON.parse(snap.projectJson);
        restoredProject.updated_at = new Date().toISOString();

        // 写入磁盘与全局状态
        await projectIpc.save(currentPath, restoredProject);
        setCurrentRecord(currentPath, restoredProject);

        await fetchSnapshots();
        toast.success(
          `已成功还原至版本 ${snap.versionTag} (${snap.name})`,
        );
        return true;
      } catch (err) {
        toast.error(`还原快照失败: ${String(err)}`);
        return false;
      }
    },
    [current, currentPath, fetchSnapshots, setCurrentRecord],
  );

  /** 衍生为新工程 (Fork project) */
  const forkSnapshot = useCallback(
    async (snapshot: ProjectSnapshot) => {
      try {
        const sourceProj: Project = JSON.parse(snapshot.projectJson);
        const newProj: Project = {
          ...sourceProj,
          id: `prj_${Date.now()}`,
          name: `${sourceProj.name} (${snapshot.versionTag} 衍生版)`,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };

        const rec = await projectIpc.createBlank();
        await projectIpc.save(rec.path, newProj);
        setCurrentRecord(rec.path, newProj);

        toast.success(`已以此快照为模板克隆并生成新工程: ${newProj.name}`);
        closeDrawer();
        return true;
      } catch (err) {
        toast.error(`衍生新工程失败: ${String(err)}`);
        return false;
      }
    },
    [closeDrawer, setCurrentRecord],
  );

  /** 删除特定快照 */
  const deleteSnapshot = useCallback(
    async (snapshotId: string) => {
      if (!projectId) return false;
      try {
        const ok = await projectIpc.snapshotDelete(projectId, snapshotId);
        if (ok) {
          await fetchSnapshots();
          toast.success("已成功清理所选历史快照");
        }
        return ok;
      } catch (err) {
        toast.error(`删除快照失败: ${String(err)}`);
        return false;
      }
    },
    [fetchSnapshots, projectId],
  );

  return {
    snapshots,
    fetchSnapshots,
    createSnapshot,
    restoreSnapshot,
    forkSnapshot,
    deleteSnapshot,
    isDrawerOpen,
    openDrawer,
    closeDrawer,
    toggleDrawer,
  };
}
