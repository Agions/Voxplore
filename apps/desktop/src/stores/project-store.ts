/**
 * SceneFab v3.0 · project store (Zustand)
 *
 * 设计:
 * - current: 当前打开的项目(M3 接入 invoke project_load)
 * - currentPath: 项目文件磁盘路径 (save / saveAs 需要)
 * - recent: 最近项目列表(M3.2 已 invoke project_list_recent)
 *
 * 与 IPC 的关系:
 * - open(path) → projectIpc.load(path) → ProjectRecord { path, project }
 *                → setCurrentRecord({ path, project })
 * - save()    → projectIpc.save(currentPath, current)
 * - saveAs(p) → projectIpc.save(p, current) → setCurrentPath(p)
 * - close()   → clear() (清空 current + currentPath)
 */

import { create } from "zustand";
import type { Project } from "../ipc/types.gen";

interface ProjectState {
  /** 当前打开的项目 (domain) */
  current: Project | null;
  /** 当前项目在磁盘上的路径 (save / saveAs 必须) */
  currentPath: string | null;
  /** 最近项目路径列表 */
  recent: string[];

  /** 一次设置 current + currentPath (open / createBlank 后调用) */
  setCurrentRecord: (path: string, project: Project) => void;
  /** 仅更新当前项目 (save 后若只想刷 updated_at 也可调) */
  setCurrent: (project: Project | null) => void;
  /** 仅更新路径 (saveAs 后调) */
  setCurrentPath: (path: string) => void;
  /** 更新最近项目列表 (project_list_recent 后调) */
  setRecent: (paths: string[]) => void;
  /** 关闭项目 (清空 current + currentPath,但保留 recent) */
  clear: () => void;
}

export const useProjectStore = create<ProjectState>()((set) => ({
  current: null,
  currentPath: null,
  recent: [],
  setCurrentRecord: (path, project) =>
    set({ current: project, currentPath: path }),
  setCurrent: (project) => set({ current: project }),
  setCurrentPath: (path) => set({ currentPath: path }),
  setRecent: (paths) => set({ recent: paths }),
  clear: () => set({ current: null, currentPath: null }),
}));
