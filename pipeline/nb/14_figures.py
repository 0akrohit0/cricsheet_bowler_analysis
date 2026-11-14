sns.set_theme(style='whitegrid', context='notebook')
TYPE_COLORS = {'pace': '#2a78d6', 'spin': '#eb6834'}
fig, axes = plt.subplots(1, 3, figsize=(17, 5.2))

# 1. Actual average vs what the context predicts
ax = axes[0]
for t, d in att.groupby('bowler_type'):
    ax.scatter(d['xAvg'], d['actual'], s=28, color=TYPE_COLORS[t], label=t, alpha=0.85, edgecolor='white', linewidth=0.6)
lim = [12, 52]
ax.plot(lim, lim, color='#898781', lw=1)
for _, r in att.nsmallest(4, 'bowler_effect').iterrows():
    ax.annotate(r['bowler'], (r['xAvg'], r['actual']), fontsize=8, xytext=(4, -3), textcoords='offset points')
ax.set(xlim=lim, ylim=lim, xlabel='Context-expected average (xAvg)', ylabel=f'Actual average, first {WICKET_WINDOW} wickets',
       title='Below the line = better than the context predicts')
ax.legend(frameon=False)

# 2. Where the real spread comes from
ax = axes[1]
vs = variance_shares.drop(['dealt', 'shaped']).sort_values('share of real variance')
colors = ['#6250d6' if i == 'bowler_effect' else '#1baf7a' if i in SHAPED else '#2a78d6' if i in DEALT else '#898781'
          for i in vs.index]
ax.barh(vs.index.str.replace('bowler_effect', 'Bowler (unexplained by context)'), 100 * vs['share of real variance'], color=colors)
ax.axvline(0, color='#c3c2b7', lw=1)
ax.set(xlabel='% of the real (noise-removed) spread in averages', title='Blue = dealt, green = shaped, violet = bowler')

# 3. Split-half: run control repeats, wicket-taking mostly doesn't
ax = axes[2]
for comp, c in [('run-control skill', '#2a78d6'), ('wicket-taking skill', '#eb6834')]:
    ax.scatter(h1[comp], h2.loc[h1.index, comp], s=22, color=c, alpha=0.8,
               label=f"{comp} (ρ = {split.loc[comp, 'reliability']:.2f})", edgecolor='white', linewidth=0.5)
ax.axhline(0, color='#c3c2b7', lw=1); ax.axvline(0, color='#c3c2b7', lw=1)
H = WICKET_WINDOW // 2
ax.set(xlabel=f'Wickets 1-{H} (log ratio vs context, + = better)', ylabel=f'Wickets {H + 1}-{WICKET_WINDOW}', title='Does the skill repeat?')
ax.legend(frameon=False, fontsize=9)
plt.tight_layout()
plt.show()
