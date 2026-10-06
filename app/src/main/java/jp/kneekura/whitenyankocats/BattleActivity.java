package jp.kneekura.whitenyankocats;

import android.app.Activity;
import android.app.AlertDialog;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Random;

public final class BattleActivity extends Activity {
    public static final String EXTRA_STAGE_KEY = "stage_key";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        String stageKey = getIntent().getStringExtra(EXTRA_STAGE_KEY);
        StageDefinition stage = GameContentStore.findStage(this, stageKey);
        if (stage == null) {
            TextView error = new TextView(this);
            error.setText("ステージ定義を読み込めません。export ZIPを再インポートしてください。");
            error.setGravity(Gravity.CENTER);
            setContentView(error);
            return;
        }

        List<UnitRecord> units = CatalogStore.load(this);
        List<EnemyRecord> enemies = GameContentStore.loadEnemies(this);
        Map<Integer, EnemyRecord> enemyById = new HashMap<>();
        for (EnemyRecord enemy : enemies) {
            enemyById.put(enemy.enemyId, enemy);
        }

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.rgb(226, 241, 247));

        TextView header = new TextView(this);
        header.setText(
                stage.category + " / " + stage.name
                        + "   城HP " + stage.baseHealth
                        + "   幅 " + stage.width
                        + "   spawn " + stage.spawns.size()
        );
        header.setTextColor(Color.BLACK);
        header.setTextSize(16);
        header.setGravity(Gravity.CENTER_VERTICAL);
        header.setPadding(dp(12), 0, dp(12), 0);
        root.addView(header, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(42)));

        BattleView battleView = new BattleView(stage, enemyById);
        root.addView(battleView, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1));

        HorizontalScrollView scroll = new HorizontalScrollView(this);
        LinearLayout unitBar = new LinearLayout(this);
        unitBar.setOrientation(LinearLayout.HORIZONTAL);
        unitBar.setPadding(dp(6), dp(4), dp(6), dp(4));

        int slots = Math.min(10, units.size());
        for (int i = 0; i < slots; i++) {
            UnitRecord unit = units.get(i);
            Button button = new Button(this);
            button.setText(String.format(
                    Locale.ROOT,
                    "%03d\n%s\n¥%d",
                    unit.unitNo,
                    unit.name,
                    unitCost(unit)
            ));
            button.setAllCaps(false);
            button.setOnClickListener(v -> battleView.deploy(unit));
            unitBar.addView(button, new LinearLayout.LayoutParams(dp(150), dp(72)));
        }

        Button allCats = new Button(this);
        allCats.setText("全キャラ");
        allCats.setOnClickListener(v -> showAllUnitPicker(battleView, units));
        unitBar.addView(allCats, new LinearLayout.LayoutParams(dp(120), dp(72)));

        Button leave = new Button(this);
        leave.setText("戻る");
        leave.setOnClickListener(v -> finish());
        unitBar.addView(leave, new LinearLayout.LayoutParams(dp(120), dp(72)));

        scroll.addView(unitBar);
        root.addView(scroll, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(80)));

        setContentView(root);
        battleView.start();
    }

    private void showAllUnitPicker(BattleView battleView, List<UnitRecord> units) {
        CharSequence[] labels = new CharSequence[units.size()];
        for (int i = 0; i < units.size(); i++) {
            UnitRecord unit = units.get(i);
            labels[i] = String.format(
                    Locale.ROOT,
                    "%03d  %s  ¥%d  再生産%dF",
                    unit.unitNo,
                    unit.name,
                    unitCost(unit),
                    unitRecharge(unit)
            );
        }

        new AlertDialog.Builder(this)
                .setTitle("出撃キャラ選択（全キャラ・第1形態）")
                .setItems(labels, (dialog, which) -> {
                    if (which >= 0 && which < units.size()) {
                        battleView.deploy(units.get(which));
                    }
                })
                .setNegativeButton("閉じる", null)
                .show();
    }

    private static int unitCost(UnitRecord unit) {
        return Math.max(0, unitStatInt(unit, 6, 0));
    }

    private static int unitRecharge(UnitRecord unit) {
        return Math.max(1, unitStatInt(unit, 7, 30));
    }

    private static int unitStatInt(UnitRecord unit, int index, int fallback) {
        try {
            return Integer.parseInt(unit.stat(index));
        } catch (Exception ignored) {
            return fallback;
        }
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private final class BattleView extends View {
        private static final int FPS = 30;
        private static final int TICK_MS = 1000 / FPS;

        private final StageDefinition stage;
        private final Map<Integer, EnemyRecord> enemyById;
        private final List<Actor> actors = new ArrayList<>();
        private final List<SpawnRuntime> spawnRuntime = new ArrayList<>();
        private final Handler handler = new Handler(Looper.getMainLooper());
        private final Random random;
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Map<Integer, Long> nextDeployFrame = new HashMap<>();

        private long frame;
        private long battleMoney = 6000;
        private final long battleMoneyMax = 99999;
        private final long passiveIncomePerTick = 5;
        private long playerBaseHp = 100_000;
        private final long playerBaseMax = 100_000;
        private long enemyBaseHp;
        private final long enemyBaseMax;
        private boolean running;
        private String resultText = "";
        private String battleMessage = "";

        BattleView(StageDefinition stage, Map<Integer, EnemyRecord> enemyById) {
            super(BattleActivity.this);
            this.stage = stage;
            this.enemyById = enemyById;
            this.enemyBaseMax = Math.max(1, stage.baseHealth);
            this.enemyBaseHp = enemyBaseMax;
            this.random = new Random(stage.key.hashCode());
            for (EnemySpawn spawn : stage.spawns) {
                spawnRuntime.add(new SpawnRuntime(spawn));
            }
            setBackgroundColor(Color.rgb(210, 234, 199));
        }

        void start() {
            if (running) {
                return;
            }
            running = true;
            handler.post(ticker);
        }

        void deploy(UnitRecord unit) {
            if (!running) {
                return;
            }

            int cost = unitCost(unit);
            long readyAt = nextDeployFrame.getOrDefault(unit.unitNo, 0L);
            if (frame < readyAt) {
                battleMessage = "再生産まで " + (readyAt - frame) + "F";
                invalidate();
                return;
            }
            if (battleMoney < cost) {
                battleMessage = "お金不足: ¥" + cost + " 必要";
                invalidate();
                return;
            }

            battleMoney -= cost;
            nextDeployFrame.put(unit.unitNo, frame + unitRecharge(unit));

            Actor actor = Actor.fromUnit(unit);
            actor.x = 120f;
            actors.add(actor);
            battleMessage = unit.name + " 出撃";
            invalidate();
        }

        private final Runnable ticker = new Runnable() {
            @Override
            public void run() {
                if (!running) {
                    return;
                }
                tick();
                invalidate();
                if (running) {
                    handler.postDelayed(this, TICK_MS);
                }
            }
        };

        private void tick() {
            frame++;
            battleMoney = Math.min(battleMoneyMax, battleMoney + passiveIncomePerTick);
            spawnEnemies();

            for (Actor actor : new ArrayList<>(actors)) {
                if (actor.hp <= 0) {
                    continue;
                }
                if (actor.cooldown > 0) {
                    actor.cooldown--;
                }
                if (actor.kbStunFrames > 0) {
                    actor.kbStunFrames--;
                    continue;
                }

                Actor target = nearestTarget(actor);
                if (target != null) {
                    float distance = Math.abs(target.x - actor.x);
                    if (distance <= actor.range) {
                        tryAttack(actor, target);
                    } else {
                        actor.x += actor.enemy ? -actor.movePerFrame : actor.movePerFrame;
                    }
                } else {
                    attackOrApproachBase(actor);
                }

                actor.x = Math.max(0f, Math.min(Math.max(stage.width, 1000), actor.x));
            }

            Iterator<Actor> iterator = actors.iterator();
            while (iterator.hasNext()) {
                Actor actor = iterator.next();
                if (actor.hp <= 0) {
                    iterator.remove();
                }
            }

            if (enemyBaseHp <= 0) {
                enemyBaseHp = 0;
                resultText = "勝利";
                running = false;
            } else if (playerBaseHp <= 0) {
                playerBaseHp = 0;
                resultText = "敗北";
                running = false;
            }
        }

        private void spawnEnemies() {
            int aliveEnemies = 0;
            for (Actor actor : actors) {
                if (actor.enemy && actor.hp > 0) {
                    aliveEnemies++;
                }
            }

            int stageLimit = stage.maxEnemyCount <= 0 ? 50 : stage.maxEnemyCount;
            for (SpawnRuntime runtime : spawnRuntime) {
                EnemySpawn spawn = runtime.spawn;
                if (aliveEnemies >= stageLimit) {
                    return;
                }
                if (!runtime.canSpawnAgain() || frame < runtime.nextFrame) {
                    continue;
                }

                int hpPercent = (int) ((enemyBaseHp * 100L) / Math.max(1L, enemyBaseMax));
                if (hpPercent > Math.max(0, spawn.spawnBasePercent)) {
                    continue;
                }

                int internalEnemyId = spawn.enemyReleaseId >= 2
                        ? spawn.enemyReleaseId - 2
                        : spawn.enemyReleaseId;
                EnemyRecord record = enemyById.get(internalEnemyId);
                if (record == null) {
                    record = new EnemyRecord(
                            internalEnemyId,
                            "Enemy " + internalEnemyId,
                            1000,
                            1,
                            5,
                            100,
                            30,
                            100,
                            0,
                            0,
                            0,
                            false,
                            1
                    );
                }

                Actor actor = Actor.fromEnemy(record, spawn.magnification);
                actor.x = Math.max(200f, stage.width - 120f);
                actors.add(actor);
                aliveEnemies++;
                runtime.spawned++;

                int min = Math.max(1, spawn.minSpawnInterval);
                int max = Math.max(min, spawn.maxSpawnInterval);
                runtime.nextFrame = frame + min
                        + (max > min ? random.nextInt(max - min + 1) : 0);
            }
        }

        private Actor nearestTarget(Actor source) {
            Actor best = null;
            float bestDistance = Float.MAX_VALUE;
            for (Actor candidate : actors) {
                if (candidate == source || candidate.enemy == source.enemy || candidate.hp <= 0) {
                    continue;
                }
                if (!source.enemy && candidate.x < source.x) {
                    continue;
                }
                if (source.enemy && candidate.x > source.x) {
                    continue;
                }
                float distance = Math.abs(candidate.x - source.x);
                if (distance < bestDistance) {
                    best = candidate;
                    bestDistance = distance;
                }
            }
            return best;
        }

        private void tryAttack(Actor attacker, Actor target) {
            if (attacker.cooldown > 0) {
                return;
            }
            applyDamage(target, Math.max(1, attacker.damage));
            attacker.cooldown = Math.max(10, attacker.attackInterval);
        }

        private void applyDamage(Actor target, long damage) {
            if (target.hp <= 0) {
                return;
            }

            long before = target.hp;
            target.hp -= Math.max(1, damage);

            if (target.hp <= 0) {
                target.hp = 0;
                if (target.enemy && before > 0) {
                    battleMoney = Math.min(
                            battleMoneyMax,
                            battleMoney + Math.max(0, target.moneyDrop)
                    );
                    if (target.moneyDrop > 0) {
                        battleMessage = target.name + " 撃破 +¥" + target.moneyDrop;
                    }
                }
                return;
            }

            int nonLethalKnockbacks = Math.max(0, target.kbCount - 1);
            if (target.kbTriggered >= nonLethalKnockbacks) {
                return;
            }

            long threshold = target.maxHp
                    * (target.kbCount - (target.kbTriggered + 1L))
                    / Math.max(1, target.kbCount);
            if (target.hp <= threshold) {
                target.kbTriggered++;
                target.kbStunFrames = 10;
                float knockbackDistance = 160f;
                target.x += target.enemy ? knockbackDistance : -knockbackDistance;
                target.x = Math.max(
                        0f,
                        Math.min(Math.max(stage.width, 1000), target.x)
                );
                battleMessage = target.name + " KB "
                        + target.kbTriggered + "/" + nonLethalKnockbacks;
            }
        }

        private void attackOrApproachBase(Actor actor) {
            if (actor.enemy) {
                float distance = actor.x;
                if (distance <= actor.range + 80) {
                    if (actor.cooldown <= 0) {
                        playerBaseHp -= Math.max(1, actor.damage);
                        actor.cooldown = Math.max(10, actor.attackInterval);
                    }
                } else {
                    actor.x -= actor.movePerFrame;
                }
            } else {
                float distance = Math.max(0, stage.width - actor.x);
                if (distance <= actor.range + 80) {
                    if (actor.cooldown <= 0) {
                        enemyBaseHp -= Math.max(1, actor.damage);
                        actor.cooldown = Math.max(10, actor.attackInterval);
                    }
                } else {
                    actor.x += actor.movePerFrame;
                }
            }
        }

        @Override
        protected void onDraw(Canvas canvas) {
            super.onDraw(canvas);
            float logicalWidth = Math.max(1000f, stage.width);
            float sx = getWidth() / logicalWidth;
            float groundY = getHeight() * 0.72f;

            paint.setColor(Color.rgb(126, 92, 55));
            canvas.drawRect(0, groundY, getWidth(), getHeight(), paint);

            paint.setColor(Color.rgb(70, 120, 180));
            canvas.drawRect(0, groundY - 110, 55, groundY, paint);
            paint.setColor(Color.rgb(190, 70, 70));
            canvas.drawRect(getWidth() - 55, groundY - 110, getWidth(), groundY, paint);

            for (Actor actor : actors) {
                float x = actor.x * sx;
                paint.setColor(actor.enemy ? Color.rgb(180, 55, 55) : Color.rgb(250, 250, 250));
                canvas.drawCircle(x, groundY - 28, actor.enemy ? 18 : 16, paint);

                paint.setTextSize(18);
                paint.setColor(Color.BLACK);
                String shortName = actor.name.length() > 8
                        ? actor.name.substring(0, 8)
                        : actor.name;
                canvas.drawText(shortName, x - 30, groundY - 52, paint);
            }

            paint.setTextSize(21);
            paint.setColor(Color.BLACK);
            canvas.drawText(
                    "自城 " + playerBaseHp + "/" + playerBaseMax
                            + "    敵城 " + enemyBaseHp + "/" + enemyBaseMax,
                    20,
                    30,
                    paint
            );
            canvas.drawText(
                    String.format(
                            Locale.ROOT,
                            "frame %d  %.1fs  30fps    所持金 ¥%d/%d",
                            frame,
                            frame / 30.0,
                            battleMoney,
                            battleMoneyMax
                    ),
                    20,
                    58,
                    paint
            );
            if (!battleMessage.isEmpty()) {
                paint.setTextSize(18);
                canvas.drawText(battleMessage, 20, 84, paint);
            }

            if (!resultText.isEmpty()) {
                paint.setTextSize(64);
                paint.setColor(Color.BLACK);
                paint.setTextAlign(Paint.Align.CENTER);
                canvas.drawText(resultText, getWidth() / 2f, getHeight() / 2f, paint);
                paint.setTextAlign(Paint.Align.LEFT);
            }
        }

        @Override
        protected void onDetachedFromWindow() {
            running = false;
            handler.removeCallbacksAndMessages(null);
            super.onDetachedFromWindow();
        }
    }

    private static final class SpawnRuntime {
        final EnemySpawn spawn;
        int spawned;
        long nextFrame;

        SpawnRuntime(EnemySpawn spawn) {
            this.spawn = spawn;
            this.nextFrame = Math.max(0, spawn.startFrame);
        }

        boolean canSpawnAgain() {
            return spawn.maxEnemyCount <= 0 || spawned < spawn.maxEnemyCount;
        }
    }

    private static final class Actor {
        final boolean enemy;
        final String name;
        final long maxHp;
        long hp;
        final float movePerFrame;
        final long damage;
        final int range;
        final int attackInterval;
        final int kbCount;
        final long moneyDrop;
        int kbTriggered;
        int kbStunFrames;
        int cooldown;
        float x;

        private Actor(
                boolean enemy,
                String name,
                long hp,
                float movePerFrame,
                long damage,
                int range,
                int attackInterval,
                int kbCount,
                long moneyDrop
        ) {
            this.enemy = enemy;
            this.name = name;
            this.maxHp = Math.max(1, hp);
            this.hp = this.maxHp;
            this.movePerFrame = Math.max(0.25f, movePerFrame);
            this.damage = Math.max(1, damage);
            this.range = Math.max(20, range);
            this.attackInterval = Math.max(10, attackInterval);
            this.kbCount = Math.max(1, kbCount);
            this.moneyDrop = Math.max(0, moneyDrop);
        }

        static Actor fromUnit(UnitRecord unit) {
            long hp = parseLong(unit.stat(0), 1000);
            int kbs = parseInt(unit.stat(1), 1);
            int speed = parseInt(unit.stat(2), 5);
            long damage = parseLong(unit.stat(3), 100);
            int attackInterval = parseInt(unit.stat(4), 30);
            int range = parseInt(unit.stat(5), 100);
            return new Actor(
                    false,
                    unit.name,
                    hp,
                    speed / 2f,
                    damage,
                    range,
                    attackInterval,
                    kbs,
                    0
            );
        }

        static Actor fromEnemy(EnemyRecord enemy, int magnification) {
            int mag = magnification <= 0 ? 100 : magnification;
            long hp = Math.max(1, enemy.hp * (long) mag / 100L);
            long damage = Math.max(1, enemy.attackDamage * (long) mag / 100L);
            long moneyDrop = Math.max(0, enemy.moneyDrop * (long) mag / 100L);
            return new Actor(
                    true,
                    enemy.name,
                    hp,
                    enemy.speed / 2f,
                    damage,
                    enemy.range,
                    enemy.attackInterval,
                    enemy.kbs,
                    moneyDrop
            );
        }

        private static int parseInt(String value, int fallback) {
            try {
                return Integer.parseInt(value);
            } catch (Exception ignored) {
                return fallback;
            }
        }

        private static long parseLong(String value, long fallback) {
            try {
                return Long.parseLong(value);
            } catch (Exception ignored) {
                return fallback;
            }
        }
    }
}