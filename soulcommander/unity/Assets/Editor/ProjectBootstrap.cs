#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

namespace SoulCommander.EditorTools
{
    // Unity 처음 열 때 회사명/게임명/기본 그래픽 설정을 한 번 자동으로 밀어넣는다.
    // 이미 값이 같으면 스킵.
    [InitializeOnLoad]
    public static class ProjectBootstrap
    {
        private const string Company = "limagination";
        private const string Product = "Soul Commander";

        static ProjectBootstrap()
        {
            EditorApplication.delayCall += ApplyOnce;
        }

        private static void ApplyOnce()
        {
            bool changed = false;
            if (PlayerSettings.companyName != Company)
            {
                PlayerSettings.companyName = Company;
                changed = true;
            }
            if (PlayerSettings.productName != Product)
            {
                PlayerSettings.productName = Product;
                changed = true;
            }
            if (changed)
            {
                AssetDatabase.SaveAssets();
                Debug.Log($"[SoulCommander] PlayerSettings 자동 설정: {Company} / {Product}");
            }
        }

        // 수동 재적용용 메뉴
        [MenuItem("Soul Commander/프로젝트 설정 재적용")]
        private static void Reapply()
        {
            PlayerSettings.companyName = Company;
            PlayerSettings.productName = Product;
            AssetDatabase.SaveAssets();
            Debug.Log($"[SoulCommander] PlayerSettings 재적용 완료: {Company} / {Product}");
        }
    }
}
#endif
