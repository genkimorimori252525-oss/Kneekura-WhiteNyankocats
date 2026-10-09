package jp.kneekura.whitenyankocats;

import android.app.Activity;
import android.app.AlertDialog;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.text.TextUtils;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.util.List;

/**
 * 「基地の i ボタン → 運営からのお知らせ」 inspired by the player's reference.
 *
 * Independent Kneekura UI; not a PONOS WebView or remote announcement feed.
 * The list is rebuilt from the currently installed, signature-verified local
 * operations revision. No URL, browser, remote image, Internet permission,
 * account/profile data or original Battle Cats save is ever used.
 */
public final class NoticeActivity extends Activity {
    private LinearLayout feed;
    private TextView sourceLabel;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        setContentView(buildPage());
    }

    @Override
    protected void onResume() {
        super.onResume();
        refresh();
    }

    private View buildPage() {
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setBackgroundColor(Color.rgb(245, 241, 231));
        page.setPadding(dp(15), dp(11), dp(15), dp(9));

        LinearLayout top = new LinearLayout(this);
        top.setGravity(Gravity.CENTER_VERTICAL);
        top.setOrientation(LinearLayout.HORIZONTAL);

        Button back = new Button(this);
        back.setText("◀ 戻る");
        back.setAllCaps(false);
        back.setContentDescription("基地に戻る");
        back.setOnClickListener(v -> finish());
        top.addView(back, new LinearLayout.LayoutParams(dp(115), dp(51)));

        TextView heading = text("にーくら運営からのお知らせ", 22, Color.rgb(43, 37, 30), true);
        heading.setGravity(Gravity.CENTER_VERTICAL);
        heading.setPadding(dp(10), 0, 0, 0);
        top.addView(heading, new LinearLayout.LayoutParams(
                0, LinearLayout.LayoutParams.WRAP_CONTENT, 1));
        page.addView(top, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(60)));

        sourceLabel = text("完全オフライン・ローカル運営データ", 13,
                Color.rgb(74, 95, 82), false);
        sourceLabel.setPadding(dp(8), dp(5), 0, dp(8));
        page.addView(sourceLabel);

        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        feed = new LinearLayout(this);
        feed.setOrientation(LinearLayout.VERTICAL);
        feed.setPadding(dp(4), dp(6), dp(4), dp(18));
        scroll.addView(feed);
        page.addView(scroll, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1));

        TextView footer = text("※ ここには、にーくら運営パックに保存されたお知らせだけを表示します。",
                12, Color.DKGRAY, false);
        footer.setGravity(Gravity.CENTER);
        page.addView(footer, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(34)));
        return page;
    }

    private void refresh() {
        feed.removeAllViews();
        try {
            LocalOpsStore.Status version = LocalOpsStore.current(this);
            if (version == null) {
                sourceLabel.setText("運営データ：未導入　／　通信なし");
                emptyMessage("まだ運営データが入ってへんで。\n基地の「運営更新」から署名付きのお知らせZIPを取り込んでな。");
                return;
            }
            sourceLabel.setText("運営データ v" + version.revision +
                    "　／　完全オフライン・署名検証済み");
            List<LocalNoticeRepository.Notice> notices = LocalNoticeRepository.current(this);
            if (notices.isEmpty()) {
                emptyMessage("現在掲載中のお知らせはありません。\n次の運営更新まで、そのままゲームを遊んでな。");
                return;
            }
            for (LocalNoticeRepository.Notice item : notices) {
                feed.addView(makeItem(item));
            }
        } catch (Exception error) {
            sourceLabel.setText("運営データの読込を停止しました");
            emptyMessage("お知らせを安全に読み込めませんでした。\n" +
                    "運営ZIPの署名・内容や、保存済みデータを確認してください。");
        }
    }

    private void emptyMessage(String message) {
        TextView note = text(message, 19, Color.DKGRAY, false);
        note.setGravity(Gravity.CENTER);
        note.setPadding(dp(24), dp(55), dp(24), dp(50));
        feed.addView(note);
    }

    private View makeItem(LocalNoticeRepository.Notice notice) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(17), dp(14), dp(17), dp(15));
        card.setBackground(rounded(Color.WHITE, Color.rgb(211, 198, 172), 13, 1));
        card.setElevation(dp(2));

        LinearLayout top = new LinearLayout(this);
        top.setOrientation(LinearLayout.HORIZONTAL);
        top.setGravity(Gravity.CENTER_VERTICAL);

        TextView category = text(notice.category, 13, Color.WHITE, true);
        category.setGravity(Gravity.CENTER);
        category.setPadding(dp(13), dp(4), dp(13), dp(4));
        category.setBackground(rounded(categoryColor(notice.category), 0, 6, 0));
        top.addView(category);

        TextView date = text(notice.date, 13, Color.DKGRAY, false);
        date.setPadding(dp(12), 0, 0, 0);
        top.addView(date);

        if (notice.pinned) {
            TextView pin = text("重要", 12, Color.rgb(168, 42, 50), true);
            pin.setGravity(Gravity.RIGHT);
            top.addView(pin, new LinearLayout.LayoutParams(
                    0, LinearLayout.LayoutParams.WRAP_CONTENT, 1));
        }
        card.addView(top);

        TextView title = text(notice.title, 19, Color.rgb(38, 36, 31), true);
        title.setPadding(0, dp(9), 0, dp(4));
        title.setMaxLines(2);
        title.setEllipsize(TextUtils.TruncateAt.END);
        card.addView(title);

        String firstLine = notice.body.replace("\r", "").split("\n", 2)[0];
        TextView lead = text(firstLine, 14, Color.rgb(91, 86, 78), false);
        lead.setMaxLines(2);
        lead.setEllipsize(TextUtils.TruncateAt.END);
        card.addView(lead);

        TextView open = text("詳しく見る  ›", 14, Color.rgb(151, 87, 42), true);
        open.setGravity(Gravity.RIGHT);
        open.setPadding(0, dp(8), 0, 0);
        card.addView(open);

        card.setOnClickListener(v -> showDetail(notice));
        card.setFocusable(true);
        card.setContentDescription(notice.date + " " + notice.category + " " +
                notice.title + " お知らせの詳細を開く");

        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        lp.setMargins(dp(2), 0, dp(2), dp(12));
        card.setLayoutParams(lp);
        return card;
    }

    private void showDetail(LocalNoticeRepository.Notice notice) {
        ScrollView scroll = new ScrollView(this);
        LinearLayout sheet = new LinearLayout(this);
        sheet.setOrientation(LinearLayout.VERTICAL);
        sheet.setPadding(dp(22), dp(15), dp(22), dp(22));

        TextView meta = text(notice.category + "　／　" + notice.date, 14,
                categoryColor(notice.category), true);
        meta.setPadding(0, 0, 0, dp(11));
        sheet.addView(meta);

        TextView body = text(notice.body, 17, Color.rgb(42, 39, 35), false);
        body.setLineSpacing(dp(4), 1.0f);
        sheet.addView(body);

        TextView note = text("\n\nにーくら運営室　／　オフラインのお知らせ",
                12, Color.GRAY, false);
        sheet.addView(note);
        scroll.addView(sheet);

        new AlertDialog.Builder(this)
                .setTitle(notice.title)
                .setView(scroll)
                .setPositiveButton("閉じる", (dialog, which) -> {})
                .show();
    }

    private TextView text(String label, int sp, int color, boolean strong) {
        TextView view = new TextView(this);
        view.setText(label);
        view.setTextSize(sp);
        view.setTextColor(color);
        if (strong) view.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        return view;
    }

    private int categoryColor(String category) {
        switch (category) {
            case "重要":
            case "不具合":
                return Color.rgb(176, 52, 57);
            case "イベント":
                return Color.rgb(66, 120, 153);
            case "ガチャ":
                return Color.rgb(153, 77, 155);
            case "更新情報":
                return Color.rgb(66, 130, 80);
            default:
                return Color.rgb(146, 111, 60);
        }
    }

    private GradientDrawable rounded(int fill, int stroke, int radius, int border) {
        GradientDrawable background = new GradientDrawable();
        background.setColor(fill);
        background.setCornerRadius(dp(radius));
        if (border > 0) background.setStroke(dp(border), stroke);
        return background;
    }

    private int dp(int px) {
        return Math.round(px * getResources().getDisplayMetrics().density);
    }
}
