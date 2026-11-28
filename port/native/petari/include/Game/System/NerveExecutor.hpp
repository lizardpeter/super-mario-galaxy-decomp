#pragma once


class Nerve;
class Spine;

class NerveExecutor {
public:
    NerveExecutor(const char* pName);

    virtual ~NerveExecutor();

    void initNerve(const Nerve* pNerve);
    void updateNerve();
    void setNerve(const Nerve* pNerve);
    bool isNerve(const Nerve* pNerve) const;
    // The authored step (1/60 s) the nerve is in (the fixed tick: ticks / k, docs/fixed-tick.md).
    s32 getNerveStep() const;
    // The nerve's counter in ticks.
    s32 getNerveTick() const;

    Spine* mSpine;
};
