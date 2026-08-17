//! vynaro-core · ServiceContainer
//!
//! 19 个核心服务的注册与解析。设计上故意不引入 DI 框架,
//! 直接用 `Arc<dyn Any + Send + Sync>` 做 type-erased storage,
//! 配以 `tokio::sync::Mutex` 保证 async 友好。
//!
//! ## 核心领域模型
//! - `register<T>` / `resolve<T>` / `try_resolve<T>`
//! - `Arc<T>` 内部存储
//!
//! ## M3+ 扩展计划
//! - 加入 "替换已有服务" API
//! - 加入 hot-reload (热重载时仅重启某个 service)
//! - 集成 toml 配置文件反序列化

use std::any::{Any, TypeId};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::Mutex;

#[derive(Debug, Default)]
pub struct ServiceContainer {
    /// type_id -> 实例的映射。仅注册一次 (重复注册 panic)。
    services: Mutex<HashMap<TypeId, Arc<dyn Any + Send + Sync>>>,
}

impl ServiceContainer {
    pub fn new() -> Self {
        Self::default()
    }

    /// 注册一个服务。重复注册同一类型会 panic (显式优于隐式)。
    pub async fn register<T: Any + Send + Sync>(&self, service: Arc<T>) {
        let id = TypeId::of::<T>();
        let mut map = self.services.lock().await;
        if map.contains_key(&id) {
            panic!(
                "service {:?} already registered",
                std::any::type_name::<T>()
            );
        }
        map.insert(id, service);
    }

    /// 解析一个服务 (返回克隆的 Arc)。
    /// 未注册返回 `VynaroError::Config`。
    pub async fn resolve<T: Any + Send + Sync>(&self) -> Result<Arc<T>, super::VynaroError> {
        let id = TypeId::of::<T>();
        let map = self.services.lock().await;
        map.get(&id)
            .and_then(|s| s.clone().downcast::<T>().ok())
            .ok_or_else(|| {
                super::VynaroError::Config(format!(
                    "service {:?} not registered",
                    std::any::type_name::<T>()
                ))
            })
    }

    /// 解析一个服务,未注册返回 None (用于可选服务)。
    pub async fn try_resolve<T: Any + Send + Sync>(&self) -> Option<Arc<T>> {
        let id = TypeId::of::<T>();
        let map = self.services.lock().await;
        map.get(&id).and_then(|s| s.clone().downcast::<T>().ok())
    }

    /// 当前已注册服务数 (主要用于单元测试断言)。
    pub async fn len(&self) -> usize {
        self.services.lock().await.len()
    }

    pub async fn is_empty(&self) -> bool {
        self.len().await == 0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct FooService {
        value: i32,
    }

    struct BarService {
        name: String,
    }

    #[tokio::test]
    async fn register_and_resolve() {
        let c = ServiceContainer::new();
        c.register(Arc::new(FooService { value: 42 })).await;

        let foo = c.resolve::<FooService>().await.unwrap();
        assert_eq!(foo.value, 42);

        // 未注册返回 None
        assert!(c.try_resolve::<BarService>().await.is_none());

        // resolve 未注册返回 Err
        assert!(c.resolve::<BarService>().await.is_err());
    }

    #[tokio::test]
    #[should_panic(expected = "already registered")]
    async fn duplicate_register_panics() {
        let c = ServiceContainer::new();
        c.register(Arc::new(FooService { value: 1 })).await;
        c.register(Arc::new(FooService { value: 2 })).await;
    }
}
