package jp.kneekura.whitenyankocats;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.Gravity;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ListView;
import android.widget.ProgressBar;
import android.widget.TextView;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public final class MainActivity extends Activity {
    private static final int REQUEST_EXPORT_ZIP = 1401;
    private static final int REQUEST_OPERATOR_PUBLIC_KEY = 1403;

    private enum Mode {
        UNITS,
        STAGES
    }

    private final List<UnitRecord> allUnits = new ArrayList<>();
    private final List<UnitRecord> shownUnits = new ArrayList<>();
    private final List<StageDefinition> allStages = new ArrayList<>();
    private final List<StageDefinition> shownStages = new ArrayList<>();

    private Mode mode = Mode.STAGES;
    private TextView statusText;
    private TextView resourceText;
    private TextView operationsText;
    private ArrayAdapter<String> adapter;
    private ProgressBar progressBar;
    private EditText searchBox;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        ProfileStore.ensureMaxed(this);
        buildUi();
        loadLocalCatalog();
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(18), dp(10), dp(18), dp(10));
        root.setBackgroundColor(Color.rgb(246, 239, 216));

        // Base top-right i: show Kneekura's own signed, offline announcements.
        LinearLayout titleBar = new LinearLayout(this);
        titleBar.setOrientation(LinearLayout.HORIZONTAL);
        titleBar.setGravity(Gravity.CENTER_VERTICAL);

        TextView title = new TextView(this);
        title.setText("にーくら大戦争 — Stage Fidelity Alpha");
        title.setTextSize(22);
        title.setTextColor(Color.BLACK);
        title.setGravity(Gravity.CENTER_VERTICAL);
        titleBar.addView(title, new LinearLayout.LayoutParams(
                0, LinearLayout.LayoutParams.MATCH_PARENT, 1));

        Button noticeButton = new Button(this);
        noticeButton.setText("i");
        noticeButton.setAllCaps(false);
        noticeButton.setTextSize(26);
        noticeButton.setTypeface(android.graphics.Typeface.DEFAULT,
                android.graphics.Typeface.BOLD);
        noticeButton.setTextColor(Color.BLACK);
        noticeButton.setContentDescription("にーくら運営からのお知らせを開く");
        android.graphics.drawable.GradientDrawable circle =
                new android.graphics.drawable.GradientDrawable();
        circle.setShape(android.graphics.drawable.GradientDrawable.OVAL);
        circle.setColor(Color.WHITE);
        circle.setStroke(dp(2), Color.rgb(40, 36, 31));
        noticeButton.setBackground(circle);
        noticeButton.setOnClickListener(v ->
                startActivity(new Intent(this, NoticeActivity.class)));
        LinearLayout.LayoutParams infoParams =
                new LinearLayout.LayoutParams(dp(45), dp(45));
        infoParams.setMargins(dp(7), 0, 0, 0);
        titleBar.addView(noticeButton, infoParams);
        root.addView(titleBar, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(51)));

        resourceText = new TextView(this);
        resourceText.setTextSize(17);
        resourceText.setTextColor(Color.rgb(125, 76, 12));
        resourceText.setPadding(0, dp(3), 0, dp(5));
        root.addView(resourceText);

        LinearLayout controls = new LinearLayout(this);
        controls.setOrientation(LinearLayout.HORIZONTAL);
        controls.setGravity(Gravity.CENTER_VERTICAL);

        Button importButton = new Button(this);
        importButton.setText("export ZIP読込");
        importButton.setOnClickListener(v -> chooseExportZip());
        controls.addView(importButton);

        Button updateButton = new Button(this);
        updateButton.setText("運営更新");
        updateButton.setOnClickListener(v -> chooseOperatorUpdate());
        updateButton.setOnLongClickListener(v -> {
            new AlertDialog.Builder(this)
                    .setTitle("運営データを戻す")
                    .setMessage("一つ前の運営データに戻すで。キャラ・ステージのクリア履歴、所持品には触れへん。")
                    .setPositiveButton("戻す", (dialog, which) -> {
                        try {
                            String message = LocalOpsStore.rollback(this);
                            refreshLocalOpsInfo();
                            new AlertDialog.Builder(this).setMessage(message)
                                    .setPositiveButton("OK", null).show();
                        } catch (Exception error) {
                            showOpsError(error);
                        }
                    })
                    .setNegativeButton("やめる", null).show();
            return true;
        });
        controls.addView(updateButton);

        Button stagesButton = new Button(this);
        stagesButton.setText("全ステージ");
        stagesButton.setOnClickListener(v -> {
            mode = Mode.STAGES;
            searchBox.setHint("マップ名 / ステージ名 / 種別 / IDで検索");
            refreshFilter(searchBox.getText().toString());
        });
        controls.addView(stagesButton);

        Button unitsButton = new Button(this);
        unitsButton.setText("キャラ");
        unitsButton.setOnClickListener(v -> {
            mode = Mode.UNITS;
            searchBox.setHint("キャラ名 / IDで検索");
            refreshFilter(searchBox.getText().toString());
        });
        controls.addView(unitsButton);

        statusText = new TextView(this);
        statusText.setTextSize(14);
        statusText.setTextColor(Color.DKGRAY);
        statusText.setPadding(dp(10), 0, 0, 0);
        controls.addView(statusText, new LinearLayout.LayoutParams(
                0, LinearLayout.LayoutParams.WRAP_CONTENT, 1));

        progressBar = new ProgressBar(this);
        progressBar.setVisibility(View.GONE);
        controls.addView(progressBar, new LinearLayout.LayoutParams(dp(34), dp(34)));

        root.addView(controls);

        operationsText = new TextView(this);
        operationsText.setTextSize(13);
        operationsText.setTextColor(Color.rgb(36, 76, 62));
        operationsText.setPadding(dp(3), dp(2), dp(3), dp(2));
        root.addView(operationsText);
        refreshLocalOpsInfo();

        searchBox = new EditText(this);
        searchBox.setHint("マップ名 / ステージ名 / 種別 / IDで検索");
        searchBox.setSingleLine(true);
        searchBox.setTextSize(15);
        root.addView(searchBox, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(48)));

        ListView listView = new ListView(this);
        adapter = new ArrayAdapter<>(this, android.R.layout.simple_list_item_1, new ArrayList<>());
        listView.setAdapter(adapter);
        listView.setOnItemClickListener((parent, view, position, id) -> {
            if (mode == Mode.UNITS) {
                if (position >= 0 && position < shownUnits.size()) {
                    showUnit(shownUnits.get(position));
                }
            } else if (position >= 0 && position < shownStages.size()) {
                launchStage(shownStages.get(position));
            }
        });
        root.addView(listView, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1));

        TextView footer = new TextView(this);
        footer.setText("全ローカルステージ解放 / MapStageData・Stage_option保持 / 完全オフライン");
        footer.setTextColor(Color.DKGRAY);
        footer.setGravity(Gravity.CENTER);
        footer.setPadding(0, dp(4), 0, 0);
        root.addView(footer);

        searchBox.addTextChangedListener(new TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {
            }

            @Override
            public void onTextChanged(CharSequence s, int start, int before, int count) {
                refreshFilter(s.toString());
            }

            @Override
            public void afterTextChanged(Editable s) {
            }
        });

        setContentView(root);
        refreshResourceBanner();
    }

    private void refreshResourceBanner() {
        Map<String, Long> resources = ProfileStore.headlineResources(this);
        StringBuilder text = new StringBuilder();
        for (String name : resources.keySet()) {
            if (text.length() > 0) {
                text.append("   ");
            }
            text.append(name).append(" MAX");
        }
        resourceText.setText(text.toString());
    }

    private void loadLocalCatalog() {
        allUnits.clear();
        allUnits.addAll(CatalogStore.load(this));
        allStages.clear();
        allStages.addAll(GameContentStore.loadStages(this));

        if (allUnits.isEmpty() && allStages.isEmpty()) {
            statusText.setText("初回: 手元の nyanko_battlecats_2026-10-06.zip を選択");
        } else {
            statusText.setText(
                    allUnits.size() + " キャラ / " + allStages.size()
                            + " ステージ / ローカル全解放"
            );
        }
        refreshFilter(searchBox.getText().toString());
    }

    private void chooseExportZip() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("*/*");
        intent.putExtra(Intent.EXTRA_MIME_TYPES, new String[]{
                "application/zip",
                "application/octet-stream"
        });
        startActivityForResult(intent, REQUEST_EXPORT_ZIP);
    }

    private void refreshLocalOpsInfo() {
        if (operationsText == null) return;
        try {
            LocalOpsStore.Status state = LocalOpsStore.current(this);
            String label = state == null ? "運営データ: 未導入" :
                    "運営データ v" + state.revision + "（署名検証済み・完全ローカル）";
            operationsText.setText(label + " ／「運営更新」でZIP選択、長押しで前版復元");
        } catch (Exception error) {
            operationsText.setText("運営データ確認エラー: " + error.getMessage());
        }
    }

    private void chooseOperatorUpdate() {
        if (!LocalOpsTrust.paired(this)) {
            new AlertDialog.Builder(this)
                    .setTitle("初回のみ：運営公開鍵を登録")
                    .setMessage("にーくら更新の署名を確認するため、PC側で発行した「jolly-ops-public.pem」を一度だけ選んでな。秘密鍵はスマホへ渡さへん。")
                    .setPositiveButton("公開鍵を選ぶ", (dialog, which) -> {
                        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                        intent.addCategory(Intent.CATEGORY_OPENABLE);
                        intent.setType("*/*");
                        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                        startActivityForResult(intent, REQUEST_OPERATOR_PUBLIC_KEY);
                    })
                    .setNegativeButton("あとで", null).show();
            return;
        }
        OfflineUpdatePicker.open(this);
    }

    private void showOpsError(Exception error) {
        new AlertDialog.Builder(this)
                .setTitle("運営データの取込みを中止")
                .setMessage(error.getClass().getSimpleName() + ": " + error.getMessage())
                .setPositiveButton("OK", null)
                .show();
    }

    private void receivedOperatorKey(Intent data) {
        Uri uri = data.getData();
        if (uri == null) return;
        setBusy(true, "公開鍵を読み込んでいます");
        new Thread(() -> {
            try {
                byte[] candidate = LocalOpsTrust.candidateFromUri(this, uri);
                String fingerprint = LocalOpsTrust.fingerprint(candidate);
                runOnUiThread(() -> {
                    setBusy(false, "公開鍵を確認してください");
                    new AlertDialog.Builder(this)
                            .setTitle("この公開鍵を信頼する？（初回だけ）")
                            .setMessage("PCで生成した公開鍵のSHA-256と同じか確認してな。\n\n" + fingerprint +
                                    "\n\n異なる鍵なら「やめる」を押す。")
                            .setPositiveButton("一致したので登録", (dialog, which) -> {
                                try {
                                    LocalOpsTrust.pinOnce(this, candidate);
                                    refreshLocalOpsInfo();
                                    new AlertDialog.Builder(this)
                                            .setMessage("公開鍵を登録したで。次からは「運営更新」を押してZIPを選ぶだけや。")
                                            .setPositiveButton("OK", null).show();
                                } catch (Exception error) {
                                    showOpsError(error);
                                }
                            })
                            .setNegativeButton("やめる", null).show();
                });
            } catch (Exception error) {
                runOnUiThread(() -> {
                    setBusy(false, "公開鍵を登録できません");
                    showOpsError(error);
                });
            }
        }, "kneekura-offline-public-key").start();
    }

    private void receivedContentBundle(Intent data) {
        setBusy(true, "署名付き更新ZIPを検証しています");
        new Thread(() -> {
            java.io.File staged = null;
            try {
                staged = OfflineUpdatePicker.stageFromResult(
                        this, OfflineUpdatePicker.REQUEST_CONTENT_UPDATE,
                        RESULT_OK, data
                );
                byte[] trusted = LocalOpsTrust.trustedKey(this);
                LocalOpsBundleVerifier.Verified verified =
                        LocalOpsBundleVerifier.verify(staged, trusted);
                final java.io.File selected = staged;
                runOnUiThread(() -> {
                    setBusy(false, "署名検証成功");
                    new AlertDialog.Builder(this)
                            .setTitle("にーくら運営更新 v" + verified.revision)
                            .setMessage("署名・ハッシュ・形式を確認したで。運営予定表だけを更新する。\n"
                                    + "戦闘やガチャへの反映は、各機能のAndroid連携が必要や。\n\n"
                                    + "端末の元ゲームやプレイヤーデータには触れへん。")
                            .setPositiveButton("適用", (dialog, which) -> {
                                setBusy(true, "運営データを保存しています");
                                new Thread(() -> {
                                    try {
                                        String message = LocalOpsStore.importVerified(this, verified);
                                        runOnUiThread(() -> {
                                            setBusy(false, message);
                                            refreshLocalOpsInfo();
                                            new AlertDialog.Builder(this).setMessage(message)
                                                    .setPositiveButton("OK", null).show();
                                        });
                                    } catch (Exception error) {
                                        runOnUiThread(() -> {
                                            setBusy(false, "更新を取り消しました");
                                            showOpsError(error);
                                        });
                                    } finally {
                                        selected.delete();
                                    }
                                }, "kneekura-offline-content-commit").start();
                            })
                            .setNegativeButton("やめる", (dialog, which) -> selected.delete())
                            .setOnCancelListener(dialog -> selected.delete())
                            .show();
                });
            } catch (Exception error) {
                if (staged != null) staged.delete();
                runOnUiThread(() -> {
                    setBusy(false, "検証に失敗しました。運営データは変更しません");
                    showOpsError(error);
                });
            }
        }, "kneekura-offline-content-check").start();
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (resultCode == RESULT_OK && data != null) {
            if (requestCode == REQUEST_OPERATOR_PUBLIC_KEY) {
                receivedOperatorKey(data);
                return;
            }
            if (requestCode == OfflineUpdatePicker.REQUEST_CONTENT_UPDATE) {
                receivedContentBundle(data);
                return;
            }
        }
        if (requestCode != REQUEST_EXPORT_ZIP || resultCode != RESULT_OK || data == null) {
            return;
        }
        Uri uri = data.getData();
        if (uri == null) {
            return;
        }

        int takeFlags = data.getFlags() & Intent.FLAG_GRANT_READ_URI_PERMISSION;
        try {
            getContentResolver().takePersistableUriPermission(uri, takeFlags);
        } catch (SecurityException ignored) {
        }

        setBusy(true, "読み込み中… キャラ・敵・全ローカルステージを復元しています");
        new Thread(() -> {
            try {
                GameImportResult imported = BattleCatsImporter.importGameFromUri(this, uri);
                CatalogStore.save(this, imported.units);
                GameContentStore.save(this, imported.enemies, imported.stages);
                ProfileStore.ensureMaxed(this);
                runOnUiThread(() -> {
                    setBusy(
                            false,
                            imported.units.size() + " キャラ / "
                                    + imported.enemies.size() + " 敵 / "
                                    + imported.stages.size() + " ステージ"
                    );
                    loadLocalCatalog();
                });
            } catch (Exception exception) {
                runOnUiThread(() -> {
                    setBusy(false, "読み込み失敗");
                    new AlertDialog.Builder(this)
                            .setTitle("import error")
                            .setMessage(exception.getClass().getSimpleName() + ": " + exception.getMessage())
                            .setPositiveButton("OK", null)
                            .show();
                });
            }
        }, "kneekura-import").start();
    }

    private void setBusy(boolean busy, String status) {
        progressBar.setVisibility(busy ? View.VISIBLE : View.GONE);
        statusText.setText(status);
    }

    private void refreshFilter(String query) {
        if (adapter == null) {
            return;
        }
        String normalized = query == null ? "" : query.trim().toLowerCase(Locale.ROOT);
        adapter.clear();

        if (mode == Mode.UNITS) {
            shownUnits.clear();
            for (UnitRecord unit : allUnits) {
                String id = Integer.toString(unit.unitNo);
                String padded = String.format(Locale.ROOT, "%03d", unit.unitNo);
                String name = unit.name.toLowerCase(Locale.ROOT);
                if (normalized.isEmpty()
                        || id.contains(normalized)
                        || padded.contains(normalized)
                        || name.contains(normalized)) {
                    shownUnits.add(unit);
                    adapter.add(String.format(
                            Locale.ROOT,
                            "%03d  %s   [取得済み / 第1形態]",
                            unit.unitNo,
                            unit.name
                    ));
                }
            }
        } else {
            shownStages.clear();
            for (StageDefinition stage : allStages) {
                String haystack = (
                        stage.category + " "
                                + stage.mapName + " "
                                + stage.stageName + " "
                                + stage.name + " "
                                + stage.key + " "
                                + stage.sourceFile
                ).toLowerCase(Locale.ROOT);
                if (normalized.isEmpty() || haystack.contains(normalized)) {
                    shownStages.add(stage);
                    String energy = stage.energy >= 0 ? Integer.toString(stage.energy) : "?";
                    String xp = stage.clearXp >= 0 ? Integer.toString(stage.clearXp) : "?";
                    adapter.add(String.format(
                            Locale.ROOT,
                            "[%s] %s / %s   統率%s XP%s ★%d 制限%d 敵%d",
                            stage.category,
                            stage.mapName,
                            stage.stageName,
                            energy,
                            xp,
                            Math.max(1, stage.starCount),
                            stage.restrictions.size(),
                            stage.spawns.size()
                    ));
                }
            }
        }
        adapter.notifyDataSetChanged();
    }

    private void launchStage(StageDefinition stage) {
        Intent intent = new Intent(this, BattleActivity.class);
        intent.putExtra(BattleActivity.EXTRA_STAGE_KEY, stage.key);
        startActivity(intent);
    }

    private void showUnit(UnitRecord unit) {
        String detail = "取得: 済み\n"
                + "使用形態: 第1形態\n\n"
                + "HP: " + unit.stat(0) + "\n"
                + "KB: " + unit.stat(1) + "\n"
                + "速度: " + unit.stat(2) + "\n"
                + "攻撃力(1): " + unit.stat(3) + "\n"
                + "射程: " + unit.stat(5) + "\n"
                + "コスト(raw): " + unit.stat(6) + "\n"
                + "再生産(raw): " + unit.stat(7) + "\n\n"
                + "raw stat fields: " + unit.firstFormStats.size();

        new AlertDialog.Builder(this)
                .setTitle(String.format(Locale.ROOT, "%03d  %s", unit.unitNo, unit.name))
                .setMessage(detail)
                .setPositiveButton("OK", null)
                .show();
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}