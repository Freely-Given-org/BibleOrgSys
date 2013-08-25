% Bible1.cls
%   Last modified: 2013-08-23 by RJH
%
% XeTeX class for layout of single-column Bibles
%
% Copyright (C) 2013 Robert Hunt
% Author: Robert Hunt <robert316@users.sourceforge.net>
% License: See gpl-3.0.txt

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{Bible}[2013/08/23 custom Bible class]
\LoadClass{book}
\RequirePackage{xltxtra} % Extra customizations for XeLaTeX -- automatically loads fontspec and xunicode
\RequirePackage{color}
\RequirePackage{lettrine} % Finds lettrine.sty


\setmainfont[Ligatures=TeX]{Charis SIL}


% Colours
\definecolor{headingColour}{rgb}{1,0.5,0}
\definecolor{verseNumberColour}{rgb}{0,0.5,1}


% \newenvironment{center}{\center}


% \RequirePackage{titlesec}

% \titleformat{\section}
%   {\Large\scshape\raggedright}
%   {}{0em}
%   {}
%   [\titlerule]
%
%   \titleformat{\subsection}
%   {\large\scshape\raggedright}
%   {}{0em}
%   {}
%
%   \newcommand{\datedsection}[2]{
%   \section[#1]{#1 \hfill #2}
% }


\newcommand{\BibleBook}[1]{
  \newpage
  \centerline{\Huge{#1}}
}

\newcommand{\BibleBookTableOfContents}{
  \tableofcontents
  \newpage
}


\newcommand{\BibleTitlePage}{
  \begin{titlepage}
  \begin{center}
}
\newcommand{\BibleIntro}{
  \end{center}
  \end{titlepage}
  \\ % Was \part but messes things up
}
\newcommand{\BibleText}{
%   \end{center} % May give an error if already closed
%   \end{titlepage}
  \\ % Was \part but messes things up
}


\newcommand{\BibleTextSection}[1]{
  \section{\textcolor{headingColour}{#1}}
}

\newcommand{\BibleSectionReference}[1]{
  \centerline{#1}
  \newline
}


% Chapter and verse numbers
\newcommand{\chapterNumber}[1]{
%     \chapter{#1}
    \lettrine[lines=3,slope=-4pt,nindent=-4pt]{#1}{~}
}
% {\em #1}

\newcommand{\verseNumber}[1]{
    \textsuperscript{\textcolor{verseNumberColour}{#1}~}
}


% Biblical titlepage paragraph styles
\newcommand{\BibleMainTitle}[1]{
    {\Huge {#1}}\\
}
\newcommand{\BibleTitleTwo}[1]{
    {\huge {#1}}\\
}
\newcommand{\BibleTitleThree}[1]{
    {\LARGE {#1}}\\
}


% Biblical introduction paragraph styles
\newcommand{\BibleParagraphStyleIP}{
    \paragraph
}


% Biblical text paragraph styles
\newcommand{\BibleParagraphStyleP}{
    \paragraph
}
\newcommand{\BibleParagraphStylePI}{
    \paragraph
}
\newcommand{\BibleParagraphStyleQ}{
    \paragraph
}
\newcommand{\BibleParagraphStyleQQ}{
    \paragraph
}
\newcommand{\BibleParagraphStyleQQQ}{
    \paragraph
}
\newcommand{\BibleParagraphStyleQQQQQ}{
    \paragraph
}


% Biblical character styles
\newcommand{\BibleCharacterStyleBK}[1]{ % Book name
    \emph{#1}
}
\newcommand{\BibleCharacterStyleQS}[1]{ % Selah
    \emph{#1}
}


% Biblical footnotes and cross-references
\newcommand{\BibleFootnote}[1]{
    \footnote{#1}
}
\newcommand{\BibleFootnoteAnchor}[1]{
    \textbf{#1}
}
\newcommand{\BibleCrossReference}[1]{
    \footnote{#1}
}
\newcommand{\BibleCrossReferenceAnchor}[1]{
    \textbf{#1}
}


% Figures
\newcommand{\BibleFigure}[1]{
    \footnote{#1}
}


% Finishing up
\newcommand{\BibleBookEnd}{
}

% \newcommand{\contact}[5]{
%     #1 {\large\textperiodcentered} #2 {\large\textperiodcentered} #3
%     {\Large} #4 \ {\Large} #5
% }
%
% \newcommand{\longcontact}[5]{
%     \center{#1 \hfill {\large\textperiodcentered} \hfill #2 \hfill {\large\textperiodcentered} \hfill #3}
%     \center{ {\Large} #4 \hfill {\Large} #5}
% }
%
% \newcommand{\workitems}[3]{
%     \begin{itemize}
%     \item #1
%     \item #2
%     \item #3
%     \end{itemize}
% }