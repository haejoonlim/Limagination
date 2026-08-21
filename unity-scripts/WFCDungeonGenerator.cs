using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

/// <summary>
/// Wave Function Collapse 기반 던전 타일 생성기.
///
/// 핵심 개념:
/// - 각 타일은 4방향(N,E,S,W)에 "소켓" 문자열을 가짐
/// - 두 타일이 인접 가능하려면 마주보는 소켓이 서로 호환되어야 함
///   (여기서는 단순화를 위해 소켓 문자열이 동일하면 호환된다고 가정.
///    필요하면 socketCompatibility 딕셔너리로 비대칭 규칙도 추가 가능)
/// - Entropy(가능한 타일 후보 수)가 가장 낮은 셀부터 붕괴(collapse)시킴
/// - 붕괴 후 이웃 셀에 제약을 전파(propagate)해서 후보를 줄임
/// - 모순(후보가 0개가 됨)이 발생하면 전체를 재시도
/// </summary>
public class WFCDungeonGenerator : MonoBehaviour
{
    [Header("Grid Settings")]
    public int width = 20;
    public int height = 20;
    public int seed = 0;
    public int maxRetries = 30;

    [Header("Tile Set")]
    public List<WFCTile> tileSet = new List<WFCTile>();

    // 내부 상태: 각 셀마다 "아직 가능한 타일 인덱스 집합"
    private List<int>[,] possibilities;
    private System.Random rng;

    // 결과: 각 셀에 최종 확정된 타일 인덱스 (-1 = 미확정/실패)
    public int[,] Result { get; private set; }

    [Serializable]
    public class WFCTile
    {
        public string name;
        [Range(0.01f, 100f)] public float weight = 1f;

        // 방향별 소켓. 예: 바닥 타일은 전부 "floor", 벽은 방향에 따라 "wall"/"floor"
        public string socketN;
        public string socketE;
        public string socketS;
        public string socketW;

        // Prefab 등 실제 스폰에 쓸 참조 (선택사항)
        public GameObject prefab;

        public string GetSocket(Dir dir)
        {
            switch (dir)
            {
                case Dir.N: return socketN;
                case Dir.E: return socketE;
                case Dir.S: return socketS;
                case Dir.W: return socketW;
            }
            return null;
        }
    }

    public enum Dir { N, E, S, W }

    private static readonly Dir[] AllDirs = { Dir.N, Dir.E, Dir.S, Dir.W };

    private static Dir Opposite(Dir d)
    {
        switch (d)
        {
            case Dir.N: return Dir.S;
            case Dir.S: return Dir.N;
            case Dir.E: return Dir.W;
            case Dir.W: return Dir.E;
        }
        return d;
    }

    private static (int dx, int dy) DirOffset(Dir d)
    {
        switch (d)
        {
            case Dir.N: return (0, 1);
            case Dir.S: return (0, -1);
            case Dir.E: return (1, 0);
            case Dir.W: return (-1, 0);
        }
        return (0, 0);
    }

    /// <summary>
    /// 두 타일이 주어진 방향으로 인접 가능한지 검사.
    /// tileA 기준 dir 방향에 tileB가 올 수 있는가.
    /// </summary>
    private bool AreCompatible(WFCTile tileA, WFCTile tileB, Dir dir)
    {
        string a = tileA.GetSocket(dir);
        string b = tileB.GetSocket(Opposite(dir));
        return a == b;
    }

    public bool Generate()
    {
        for (int attempt = 0; attempt < maxRetries; attempt++)
        {
            rng = new System.Random(seed + attempt);
            if (TryGenerateOnce())
            {
                Debug.Log($"[WFC] 성공 (attempt {attempt + 1})");
                return true;
            }
        }
        Debug.LogWarning("[WFC] 모든 재시도 실패. maxRetries를 늘리거나 타일셋/규칙을 점검하세요.");
        return false;
    }

    private bool TryGenerateOnce()
    {
        int tileCount = tileSet.Count;
        possibilities = new List<int>[width, height];
        for (int x = 0; x < width; x++)
            for (int y = 0; y < height; y++)
                possibilities[x, y] = Enumerable.Range(0, tileCount).ToList();

        while (true)
        {
            var target = FindLowestEntropyCell();
            if (target == null)
            {
                // 모든 셀이 확정됨 -> 성공
                BuildResult();
                return true;
            }

            var (cx, cy) = target.Value;
            var candidates = possibilities[cx, cy];

            if (candidates.Count == 0)
                return false; // 모순 발생, 재시도 필요

            int chosen = WeightedPick(candidates);
            possibilities[cx, cy] = new List<int> { chosen };

            if (!Propagate(cx, cy))
                return false; // 전파 중 모순 발생
        }
    }

    private (int, int)? FindLowestEntropyCell()
    {
        int bestEntropy = int.MaxValue;
        List<(int, int)> bestCells = new List<(int, int)>();

        for (int x = 0; x < width; x++)
        {
            for (int y = 0; y < height; y++)
            {
                int count = possibilities[x, y].Count;
                if (count <= 1) continue; // 이미 확정됨

                if (count < bestEntropy)
                {
                    bestEntropy = count;
                    bestCells.Clear();
                    bestCells.Add((x, y));
                }
                else if (count == bestEntropy)
                {
                    bestCells.Add((x, y));
                }
            }
        }

        if (bestCells.Count == 0) return null;
        return bestCells[rng.Next(bestCells.Count)];
    }

    private int WeightedPick(List<int> candidateIndices)
    {
        float totalWeight = candidateIndices.Sum(i => tileSet[i].weight);
        float roll = (float)(rng.NextDouble() * totalWeight);
        float cumulative = 0f;

        foreach (int idx in candidateIndices)
        {
            cumulative += tileSet[idx].weight;
            if (roll <= cumulative)
                return idx;
        }
        return candidateIndices[candidateIndices.Count - 1];
    }

    /// <summary>
    /// (cx, cy)가 확정된 이후, 이웃 셀들의 후보를 줄이고
    /// 변화가 생기면 그 이웃의 이웃으로 계속 전파(BFS).
    /// </summary>
    private bool Propagate(int cx, int cy)
    {
        var queue = new Queue<(int, int)>();
        queue.Enqueue((cx, cy));

        while (queue.Count > 0)
        {
            var (x, y) = queue.Dequeue();
            var currentCandidates = possibilities[x, y];

            foreach (var dir in AllDirs)
            {
                var (dx, dy) = DirOffset(dir);
                int nx = x + dx, ny = y + dy;
                if (nx < 0 || nx >= width || ny < 0 || ny >= height) continue;

                var neighborCandidates = possibilities[nx, ny];
                if (neighborCandidates.Count <= 1) continue; // 이미 확정, 더 줄일 필요 없음

                int before = neighborCandidates.Count;

                // neighbor 후보 중, currentCandidates의 "어떤 타일과도" 호환 안 되는 것 제거
                neighborCandidates.RemoveAll(nIdx =>
                    !currentCandidates.Any(cIdx => AreCompatible(tileSet[cIdx], tileSet[nIdx], dir))
                );

                if (neighborCandidates.Count == 0)
                    return false; // 모순

                if (neighborCandidates.Count != before)
                    queue.Enqueue((nx, ny));
            }
        }
        return true;
    }

    private void BuildResult()
    {
        Result = new int[width, height];
        for (int x = 0; x < width; x++)
            for (int y = 0; y < height; y++)
                Result[x, y] = possibilities[x, y].Count == 1 ? possibilities[x, y][0] : -1;
    }

    /// <summary>
    /// 결과를 실제 씬에 스폰. tile.prefab이 설정되어 있어야 함.
    /// </summary>
    public void Instantiate(Transform parent, float cellSize = 1f)
    {
        if (Result == null)
        {
            Debug.LogWarning("[WFC] Generate()를 먼저 호출하세요.");
            return;
        }

        for (int x = 0; x < width; x++)
        {
            for (int y = 0; y < height; y++)
            {
                int idx = Result[x, y];
                if (idx < 0) continue;
                var tile = tileSet[idx];
                if (tile.prefab == null) continue;

                Vector3 pos = new Vector3(x * cellSize, 0, y * cellSize);
                Instantiate(tile.prefab, pos, Quaternion.identity, parent);
            }
        }
    }
}

/*
=========================================================
사용 예시 (인스펙터에서 tileSet 채우는 대신 코드로도 가능):
=========================================================

var floor = new WFCDungeonGenerator.WFCTile {
    name = "Floor", weight = 5f,
    socketN = "floor", socketE = "floor", socketS = "floor", socketW = "floor"
};

var wallH = new WFCDungeonGenerator.WFCTile {
    name = "WallHorizontal", weight = 2f,
    socketN = "wall", socketE = "wall_end", socketS = "floor", socketW = "wall_end"
};

var doorway = new WFCDungeonGenerator.WFCTile {
    name = "Door", weight = 1f,
    socketN = "wall", socketE = "floor", socketS = "floor", socketW = "floor"
};

// 소켓 문자열을 잘 설계하는 게 WFC 결과 품질의 8할입니다.
// - "floor"-"floor" 는 인접 가능
// - "wall"-"wall" 은 인접 가능 (벽이 이어짐)
// - "wall"-"floor" 는 인접 불가능하게 설계해야 벽이 바닥 한가운데 안 튀어나옴
// 소켓을 세밀하게 나눌수록(예: wall_top, wall_side) 더 정교한 던전 형태가 나옵니다.

=========================================================
확장 아이디어:
=========================================================
1. 모순 발생 시 "전체 재시도"가 아니라 "직전 몇 단계만 되돌리는 backtracking"을
   추가하면 큰 그리드(50x50 이상)에서 성공률이 크게 오릅니다.
2. 방(room) 단위로 먼저 배치하고 그 사이를 WFC로 복도 채우는 하이브리드 방식이
   실전 던전 생성에서 더 자연스러운 결과를 냅니다.
3. socketCompatibility를 Dictionary<(string,string), bool> 으로 확장하면
   "wall은 half_wall과도 붙을 수 있다" 같은 비대칭 규칙을 넣을 수 있습니다.
=========================================================
*/
