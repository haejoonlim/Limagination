using System;
using System.IO;
using UnityEngine;

namespace SoulCommander.Save
{
    // 원자성 세이브 규칙:
    //   1) 임시파일(.tmp)에 쓴다
    //   2) fsync 대체 (Flush + Close)
    //   3) File.Replace 로 원본을 원자 교체 (백업 옵션)
    //   4) 로드 시 JSON 파싱 실패하면 .corrupt.bak 로 옮기고 신규 세이브 반환
    //
    // 세션 격리: sessionKey 로 파일명을 구분한다. EditMode 테스트가 실제 게임 세이브를 덮지 않도록.
    public class SaveManager
    {
        public readonly string Directory;
        public readonly string SessionKey;

        private const string Ext = ".json";
        private const string TmpExt = ".tmp";
        private const string CorruptExt = ".corrupt.bak";

        public string FilePath => Path.Combine(Directory, $"save_{SessionKey}{Ext}");
        public string TmpPath => Path.Combine(Directory, $"save_{SessionKey}{TmpExt}");
        public string CorruptPath => Path.Combine(Directory, $"save_{SessionKey}{CorruptExt}");

        public SaveManager(string directory, string sessionKey)
        {
            Directory = directory ?? throw new ArgumentNullException(nameof(directory));
            SessionKey = string.IsNullOrEmpty(sessionKey) ? "default" : sessionKey;
            if (!System.IO.Directory.Exists(Directory))
                System.IO.Directory.CreateDirectory(Directory);
        }

        public static SaveManager ForPlayer()
        {
            return new SaveManager(Application.persistentDataPath, "player");
        }

        public void Save(SaveData data)
        {
            if (data == null) throw new ArgumentNullException(nameof(data));
            data.updatedAt = DateTime.UtcNow.ToString("o");
            if (string.IsNullOrEmpty(data.createdAt)) data.createdAt = data.updatedAt;

            string json = JsonUtility.ToJson(data, true);

            // 1) 임시파일 작성 + flush
            using (var fs = new FileStream(TmpPath, FileMode.Create, FileAccess.Write, FileShare.None))
            using (var w = new StreamWriter(fs))
            {
                w.Write(json);
                w.Flush();
                fs.Flush(true); // OS-level flush
            }

            // 2) 원자 교체
            if (File.Exists(FilePath))
            {
                // File.Replace 는 destination 존재 필수
                File.Replace(TmpPath, FilePath, null);
            }
            else
            {
                File.Move(TmpPath, FilePath);
            }
        }

        // 없으면 신규 SaveData 반환, 손상되면 .corrupt.bak 로 옮기고 신규 반환.
        // wasCorrupted 로 손상 여부를 알림.
        public SaveData Load(out bool wasCorrupted)
        {
            wasCorrupted = false;
            if (!File.Exists(FilePath))
            {
                return new SaveData();
            }
            string json;
            try { json = File.ReadAllText(FilePath); }
            catch (Exception e)
            {
                Debug.LogError($"[SaveManager] 읽기 실패: {e.Message}");
                MoveToCorrupt();
                wasCorrupted = true;
                return new SaveData();
            }

            SaveData parsed = null;
            try { parsed = JsonUtility.FromJson<SaveData>(json); }
            catch (Exception e)
            {
                Debug.LogWarning($"[SaveManager] JSON 파싱 예외: {e.Message}");
            }

            // JsonUtility 는 실패 시 null 리턴 (예외 안 던지는 경우도 있음)
            if (parsed == null || parsed.schemaVersion <= 0)
            {
                MoveToCorrupt();
                wasCorrupted = true;
                return new SaveData();
            }
            SaveMigration.Migrate(parsed);
            return parsed;
        }

        public SaveData Load() => Load(out _);

        private void MoveToCorrupt()
        {
            try
            {
                if (File.Exists(CorruptPath)) File.Delete(CorruptPath);
                File.Move(FilePath, CorruptPath);
                Debug.LogWarning($"[SaveManager] 손상 세이브를 격리: {CorruptPath}");
            }
            catch (Exception e)
            {
                Debug.LogError($"[SaveManager] .corrupt.bak 이동 실패: {e.Message}");
            }
        }

        public void DeleteAll()
        {
            if (File.Exists(FilePath)) File.Delete(FilePath);
            if (File.Exists(TmpPath)) File.Delete(TmpPath);
            if (File.Exists(CorruptPath)) File.Delete(CorruptPath);
        }
    }
}
